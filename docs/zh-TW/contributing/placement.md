---
title: "擺放與轉換順序"
sidebar: development
---

cell 以 reference 擺放它的部件：`ref = c << part` 把 cell `part` 放進 `c` 而不複製它，`ref.drotate`、`ref.dmirror_y`、`ref.dmove` 與 `ref.connect` 決定它放在哪裡。以下規則說明該用哪一種轉換、以什麼順序，因為順序會改變結果。

本頁用到的名詞：

- **Reference**：一個 cell 在另一個 cell 中的一次擺放，有自己的旋轉、鏡射與位置；cell 本身是共用的。
- **Port**：cell 邊緣上一個具名的點，有寬度與以度表示的方向，是其他部件連接的地方。
- **DBU**（資料庫單位）：GDS 儲存的整數格點；這裡 1 DBU 是 1 nm。

本頁範例可以單獨執行，依序執行。它們共用以下設定。

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point

activate()
LAYER = (1, 0)


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def bounds(ref):
    return ref.dxmin, ref.dxmax, ref.dymin, ref.dymax
```

## R2. 原地轉動部件時繞它的中心；放到圓上時要刻意為之 {#r2}

**規則。** 要讓部件在原處轉動，傳入它的中心：`ref.drotate(angle, center=ref.dcenter)`。要把部件放到圓上，先轉動它，再移動到 `polar_point(radius, angle)`。

不帶中心的 `ref.drotate(angle)` 會繞著所在 cell 的原點轉動部件，所以先被移到某處的部件會繞著那個原點甩出去。只有在你本來就要把部件放到以原點為圓心的圓上時，這才是對的，而程式碼應該寫明這一點。

![**問題。** 一個 4 × 2 µm 的部件先移到 x = 10 µm，再繞原點轉 90°：它甩到 x = −2…0 µm、y = 10…14 µm。虛線輪廓是它原本應該轉到的位置。](../_static/images/contributing/r2-problem.svg)

![**結果。** 同一個部件繞自己的中心轉 90°，仍留在 (12, 1) µm 附近。](../_static/images/contributing/r2-result.svg)

```python
part = gf.components.rectangle(size=(4, 2), layer=LAYER)


def turned(about_centre):
    c = gf.Component()
    ref = c << part
    ref.dmove((10, 0))
    if about_centre:
        ref.drotate(90, center=ref.dcenter)  # do: turns in place
    else:
        ref.drotate(90)  # turns about the parent's origin
    return c, ref


assert bounds(turned(about_centre=False)[1]) == pytest.approx((-2, 0, 10, 14))
assert bounds(turned(about_centre=True)[1]) == pytest.approx((11, 13, -1, 3))
```

放到圓上可以讀成兩個步驟：轉動一個以原點為中心的部件，再沿著該角度把它移出去。

```python
spoke = gf.components.rectangle(size=(4, 2), centered=True, layer=LAYER)


def on_a_circle(radius, angles):
    c = gf.Component()
    for angle in angles:
        ref = c << spoke
        ref.drotate(angle)  # centred on the origin, so this turns it in place
        ref.dmove(polar_point(radius, angle))
    return c


ring = on_a_circle(20, (0, 90, 180, 270))
centres = [tuple(ref.dcenter) for ref in ring.insts]
assert centres == pytest.approx([(20, 0), (0, 20), (-20, 0), (0, -20)])
```

**如何檢查。** 在 cell 的測試中，以 `ref.dxmin`、`ref.dxmax`、`ref.dymin` 與 `ref.dymax` 斷言擺放後部件的範圍，或斷言它的 port 位置。

## R3. 轉換 reference，絕不轉換共用的 cell {#r3}

**說明。** 由 `@gf.cell` 工廠建立的 cell 會被快取：以相同參數呼叫的每個呼叫者都拿到同一個 cell。GDSFactory 會鎖住它，所以修改它會引發錯誤，而不是對所有使用者一起改變。請轉換你擺放的 reference。若要改變形狀本身，請在副本上操作：`editable = cell.copy()`。

```python
with pytest.raises(RuntimeError, match="locked"):
    part.drotate(30)  # part is the cached rectangle cell

editable = part.copy()
editable.add_polygon(box(0, 0, 1, 1), layer=LAYER)  # a copy is not locked
```

這是一則說明，而不是附圖的建構規則：GDSFactory 已經強制執行它。

## R4. 鏡射與旋轉不可交換：把鏡射的部件連接到它的 port {#r4}

**規則。** 先鏡射再旋轉，和先旋轉再鏡射並不相同。擺放鏡射的部件時，使用 `ref.connect(port, target, mirror=True)`，由它必須對上的 port 同時決定兩者，並檢查一個 port 的方向。

在 30° 時，兩種順序的結果相差 60°。手寫這兩步容易寫錯順序，而不對稱的部件只有在仔細檢視時才看得出來。

![**問題。** 一個 L 形標記對 x 軸鏡射並旋轉 30°，兩種順序：青綠色先鏡射，琥珀色先旋轉。箭頭是它的 port `m`：第一種順序為 30°，第二種為 330°。](../_static/images/contributing/r4-problem.svg)

![**結果。** 以 `mirror=True` 把標記連接到朝向 210° 的目標 port（灰色箭頭）：它的 port `m`（深色箭頭）位在目標上，朝向 30°，與目標相反。](../_static/images/contributing/r4-result.svg)

```python
marker = gf.Component()
marker.add_polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)], layer=LAYER)  # an L, so a mirror shows
marker.add_port("m", center=(4, 0.5), width=1, orientation=0, layer=LAYER)


def mirrored_and_rotated(mirror_first):
    c = gf.Component()
    ref = c << marker
    if mirror_first:
        ref.dmirror_y()  # across the x axis
        ref.drotate(30)
    else:
        ref.drotate(30)
        ref.dmirror_y()
    return c, ref


assert mirrored_and_rotated(mirror_first=True)[1].ports["m"].orientation == pytest.approx(30)
assert mirrored_and_rotated(mirror_first=False)[1].ports["m"].orientation == pytest.approx(330)

target = gf.Component()
target.add_port("t", center=(10, 10), width=1, orientation=210, layer=LAYER)


def connected_mirrored():
    c = gf.Component()
    anchor = c << target
    ref = c << marker
    ref.connect("m", anchor.ports["t"], mirror=True)
    return c, ref


connected = connected_mirrored()[1]
assert connected.ports["m"].orientation == pytest.approx(30)
# connect rounds the placement to the grid, so the port lands within 1 nm of the target (R13)
assert tuple(connected.ports["m"].dcenter) == pytest.approx((10, 10), abs=0.001)
```

**如何檢查。** 組合完成後，以 `pytest.approx` 斷言鏡射部件中一個 port 的方向與位置，因為旋轉 30° 得到的是 29.999999999999993，而不是 30。

## R13. 以 `connect` 在 port 處接合部件，並在局部座標系中進行 {#r13}

**規則。** 以連接 port 的方式接合兩個部件，`ref.connect(port, other.ports[name])`，而不是把各部件移到你算出來的位置。連接 port 朝向 0°、90°、180° 或 270° 的部件，再把合併後的結果旋轉一次（[R1](one-outline.md#r1)）。

你算出來的位置，例如落在奇數個奈米一半處的中心，會在擺放時被捨入，部件之間可能相差 1 nm。`connect` 則把一個 port 精確放在另一個 port 上。Purcell IDC 的梳狀電極與錐形段原本是以各自捨入的中心移動來擺放；寬 63.225 µm（奇數個 DBU）的梳狀電極因此在一側留下 1 nm 的狹縫（[#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58)，A1，於 [#61](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/pull/61) 修正）。

![**問題。** 63.225 µm 的梳狀電極移動半個寬度，導線移到算出來的梳狀電極邊緣：兩個多邊形。放大圖顯示 1 nm 的狹縫。](../_static/images/contributing/r13-problem.svg)

![**結果。** 同一條導線連接到梳狀電極的 port：一個多邊形。放大圖顯示同一個位置。](../_static/images/contributing/r13-result.svg)

```python
def comb(width):
    c = gf.Component()
    c.add_polygon(box(0, 0, width, 10), layer=LAYER)
    c.add_port("e", center=(width, 5), width=10, orientation=0, layer=LAYER)
    return c


lead = gf.Component()
lead.add_polygon(box(0, -5, 20, 5), layer=LAYER)
lead.add_port("w", center=(0, 0), width=10, orientation=180, layer=LAYER)


def comb_and_lead(width, use_connect):
    c = gf.Component()
    body = c << comb(width)
    body.dmove((-width / 2, 0))  # centred on x = 0
    tail = c << lead
    if use_connect:
        tail.connect("w", body.ports["e"])  # do
    else:
        tail.dmove((width / 2, 5))  # don't: a second, separately rounded position
    return c


def polygons(component):
    return component.get_region(LAYER, merge=True).count()


assert polygons(comb_and_lead(63.225, use_connect=False)) == 2
assert polygons(comb_and_lead(63.225, use_connect=True)) == 1
```

`connect` 會把被接上的部件位置捨入到格點。在 0°、90°、180° 與 270° 時，port 都在格點上，部件會精確相接。在其他角度，你所連接的 port 不在格點上，捨入後的部件可能與它相差 1 nm：一根長 9.364 µm、寬 3.3 µm 的導條以 0.3° 為步進旋轉，末端再連接一根寬 6.1 µm 的導條，在 1200 個角度中有 312 個分成兩個多邊形。

```python
def bar(length, width):
    c = gf.Component()
    c.add_polygon(box(0, -width / 2, length, width / 2), layer=LAYER)
    c.add_port("w", center=(0, 0), width=width, orientation=180, layer=LAYER)
    c.add_port("e", center=(length, 0), width=width, orientation=0, layer=LAYER)
    return c


def connected_at(angle):  # don't: connect to a port that faces an arbitrary angle
    c = gf.Component()
    first = c << bar(9.364, 3.3)
    first.drotate(angle)
    second = c << bar(7.405, 6.1)
    second.connect("w", first.ports["e"], allow_width_mismatch=True)
    return c


ANGLES = [step * 0.3 for step in range(1200)]
assert sum(polygons(connected_at(angle)) > 1 for angle in ANGLES) == 312
```

**如何檢查。** 在 cell 的測試中計算每個導體合併後的多邊形數量（[R8](construction-checks.md)）：1 nm 的狹縫會把導體分成兩塊。
