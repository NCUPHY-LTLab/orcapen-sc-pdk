---
title: "先成為一個輪廓，再一次轉換與圓角"
sidebar: development
---

由多個部件畫成的導體，要等各部件成為一個輪廓之後才安全。每個重新計算座標的操作（旋轉、圓角、布林運算）都會把每個頂點再捨入到 1 nm 格點一次，而仍然分開的部件會各自被捨入。以下三條規則對旋轉、圓角與組合說的是同一件事：先做成一個輪廓，再轉換或圓角一次。

本頁用到的名詞：

- **DBU**（資料庫單位，database unit）：GDS 儲存座標所用的整數格點。本 PDK 的 1 DBU 是 1 nm。
- **局部座標系**：你繪製形狀所在的 cell 的座標系，在任何旋轉或移動把它放進父 cell 之前。
- **合併**：像光罩寫入器一樣，把一個圖層中重疊與相接的多邊形併成最少的多邊形。`component.get_region(layer, merge=True)` 傳回合併後的圖層。

本頁範例可以單獨執行，依序在儲存庫根目錄以 `PYTHONPATH=tests` 執行（供 `geometry_checks` 匯入）。它們共用以下設定。

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point

activate()
LAYER = (1, 0)


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def merged(component):
    return component.get_region(LAYER, merge=True)


def short_edges(component):
    """Edges of the merged layer shorter than 2 DBU.

    Pass all three arguments: KLayout reads ``with_length(0, 2)`` as
    "length is not 0" (a length and an ``inverse`` flag).
    """
    return merged(component).edges().with_length(0, 2, False).count()
```

## R1. 剛體形狀的各部件先在局部座標系合併，再一次旋轉與移動 {#r1}

**規則。** 在一個局部座標系中畫出剛體形狀的所有部件，在那裡把它們合併成一個輪廓，然後才旋轉與移動這個輪廓。

一個部件的角若落在另一個部件的邊上（T 形接點），它是一個多邊形的頂點，卻不是另一個多邊形的頂點。旋轉之後，每個多邊形的頂點各自捨入，這個角便不再落在另一條邊上，合併後在它旁邊留下一條 1 DBU 的邊。在局部座標系中合併時，每個座標都是精確的，T 形接點在任何捨入之前就消失了。

![**問題。** 同一座標系中的兩個部件，以兩個多邊形的形式旋轉 76.5°。放大圖聚焦在 T 形接點，合併後的輪廓在那裡有一條 1 DBU 的邊（已標出）。](../_static/images/contributing/r1-problem.svg)

![**結果。** 同樣的部件先在局部座標系合併，再旋轉 76.5°。放大圖顯示同一個位置，沒有過短的邊。](../_static/images/contributing/r1-result.svg)

```python
PARTS = [(0, 9.364, 3.3), (9.364, 16.769, 6.1)]  # x0, x1, height in µm; the parts share x = 9.364


def parts_in_one_frame():
    local = gf.Component()
    for x0, x1, height in PARTS:
        local.add_polygon(box(x0, 0, x1, height), layer=LAYER)
    return local


def rotated_parts(angle):  # don't: the parts stay two polygons through the rotation
    c = gf.Component()
    ref = c << parts_in_one_frame()
    ref.drotate(angle)
    ref.dmove((5, 5))
    return c


def rotated_outline(angle):  # do: merge in the local frame, then rotate and move once
    outline = gf.Component()
    outline.add_polygon(merged(parts_in_one_frame()), layer=LAYER)
    c = gf.Component()
    ref = c << outline
    ref.drotate(angle)
    ref.dmove((5, 5))
    return c


def rotated_one_by_one(angle):  # don't either: each part rotated and moved on its own
    c = gf.Component()
    for x0, x1, height in PARTS:
        part = gf.Component()
        part.add_polygon(box(0, 0, x1 - x0, height), layer=LAYER)
        ref = c << part
        ref.drotate(angle)
        ref.dmove(polar_point(x0, angle))
    return c
```

`polar_point(radius, angle)` 來自 `orcapen_sc_pdk.helpers.layout.geometry`，傳回該半徑與角度（以度為單位）的點。把旋轉角掃過 1200 個角度，計算每種建構方式留下的過短邊：

```python
ANGLES = [step * 0.3 for step in range(1200)]  # 0° to 359.7° in 0.3° steps
assert short_edges(rotated_parts(76.5)) == 1
assert short_edges(rotated_outline(76.5)) == 0
assert sum(short_edges(rotated_parts(angle)) > 0 for angle in ANGLES) == 12
assert sum(short_edges(rotated_one_by_one(angle)) > 0 for angle in ANGLES) == 28
assert sum(short_edges(rotated_outline(angle)) > 0 for angle in ANGLES) == 0
```

在 1200 個角度中，兩個多邊形一起旋轉時，有 12 個角度留下 1 DBU 的邊；部件逐一旋轉時有 28 個。合併後的輪廓一個也沒有。若共用座標不在格點上，逐一旋轉部件還會把導體切開（[R9](grid-and-polygons.md#r9)）。

**如何檢查。** 像上面那樣掃過旋轉角並計算過短的邊。在 cell 的測試中，`construction_report` 會回報每一條短於 2 DBU 的邊（[R8](construction-checks.md)）。

## R6. 先聯集各部件，只做一次圓角，並以延伸再裁切保留方形端 {#r6}

**規則。** 在導體所有部件都接合之後才對角做圓角。若要保留某一端為方形，先把輪廓延伸超過該端，做圓角，再把延伸的部分裁掉。

先對一個部件做圓角、再加上另一個部件，會在圓角與新部件相接處留下缺口：那個角已經不再是角，卻被做了圓角。在 `disk_flip_chip_qubit` 中，先對爪形電極做圓角再加上錐形段，留下了 58–65° 的尖刺與 16–93 nm 的折線（[#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53)，原因 2）。

也不要用圓形視窗限制圓角的範圍：把圓角後的片段切開再拼接回去，切點會捨入到相差 1 DBU 的位置。同一個爪形電極因此留下長 1.3 µm 與 2.3 µm 的零寬度狹縫（[#47](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/47)，C2 與 C3）。

![**問題。** 20 µm 的爪形電極與 10 µm 的錐形段，各自以 3 µm 半徑做圓角後再接合。放大圖聚焦在 x = 20 µm 的缺口，兩個圓角在那裡相接。](../_static/images/contributing/r6-problem.svg)

![**結果。** 各部件先接合，只做一次圓角。右端的方形是先把輪廓延伸 6 µm、做圓角，再裁回 x = 30 µm 而保留的。](../_static/images/contributing/r6-result.svg)

```python
RADIUS = gf.kcl.to_dbu(3)  # the 3 µm corner radius in DBU; KLayout's rounding works in DBU
CLAW, TAPER = (0, 0, 20, 10), (20, 0, 30, 10)


def region(*boxes):
    """Boxes in µm as one merged region in DBU."""
    c = gf.Component()
    for corners in boxes:
        c.add_polygon(box(*corners), layer=LAYER)
    return merged(c)


def rounded(shape):
    return shape.rounded_corners(RADIUS, RADIUS, 64)  # inner radius, outer radius, points per circle


round_then_join = (rounded(region(CLAW)) + rounded(region(TAPER))).merged()  # don't
join_then_round = rounded(region(CLAW, TAPER))  # do
extended = rounded(region(CLAW, (20, 0, 30 + 2 * 3, 10)))  # run the outline 6 µm past the end
square_end = extended & region((-1, -1, 30, 11))  # and clip it back at x = 30


def area_um2(shape):
    return shape.area() * gf.kcl.dbu**2


assert round(area_um2(round_then_join ^ join_then_round), 3) == 7.702  # the notches at x = 20
corners = {(point.x, point.y) for point in next(square_end.each()).each_point_hull()}
assert {(30_000, 0), (30_000, 10_000)} <= corners  # the right end keeps its square corners
assert (0, 0) not in corners  # the left end is rounded
```

兩種建構方式相差 7.702 µm²：x = 20 µm 上下兩處的缺口，那裡有四個角被做了圓角，但它們並不是接合後導體的角。

**如何檢查。** 缺口不是孔洞、不是過短的邊，也不是自我相交，所以只有和你想要的形狀比較才找得到。把預期形狀傳給 `construction_report`，它會回報圖層與預期形狀不同的地方（[R8](construction-checks.md)）。

```python
from geometry_checks import construction_report  # tests/geometry_checks.py


def as_component(shape):
    c = gf.Component()
    c.add_polygon(shape, layer=LAYER)
    return c


notched = construction_report(as_component(round_then_join), intended={LAYER: join_then_round})
assert notched[LAYER].holes.is_empty() and notched[LAYER].min_edge_dbu >= 2
assert any("differs from the intended shape" in defect for defect in notched[LAYER].defects)
```

## R12. 以布林運算組合形狀，不要串接它們的點列 {#r12}

**規則。** 把每個部件建成封閉的形狀，再以布林運算（聯集、差集、交集）組合；絕不把各部件的點列串接成一個多邊形。

串接而成的點列，只有在每一段方向都正確、每個接點都剛好落在下一段起點時，才是有效的多邊形。只要有一處不符合，多邊形就會與自己交叉或重疊，而它如何被儲存取決於 KLayout 對那個多邊形的處理方式，而不是你的本意。範例中，一塊帶圓形淨空區的接地方塊被畫成一個點列；當圓弧的方向相反時，輪廓會折回並與自己重疊，淨空區就這樣消失，沒有任何錯誤。布林運算則不論圓弧方向如何，都得到同樣的形狀。把圓角後的爪形片段以點列拼接，正是 [#47](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/47) C2 與 C3 那些零寬度狹縫的來源；重建後的 disk qubit 輪廓改用對形狀的布林運算（[#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53)）。

![**問題。** 40 µm 的接地方塊，在上緣拼接一段 8 µm 的淨空區圓弧，但圓弧的方向列反了。虛線是預期的淨空區；儲存下來的多邊形沒有淨空區。](../_static/images/contributing/r12-problem.svg)

![**結果。** 同一塊接地以 `gf.boolean` 建成方塊減去淨空區圓形。](../_static/images/contributing/r12-result.svg)

```python
def arc(center, radius, start, stop, segments):
    return [polar_point(radius, start + (stop - start) * i / segments, center) for i in range(segments + 1)]


CLEARANCE = arc((0, 20), 8, 0, -180, 32)  # from (8, 20) down and round to (-8, 20)


def ground_from_points(clearance):  # don't: one polygon spliced from point lists
    c = gf.Component()
    c.add_polygon([(-20, -20), (20, -20), (20, 20)] + clearance + [(-20, 20)], layer=LAYER)
    return c


def ground_from_shapes():  # do: a square minus a circle
    square = gf.Component()
    square.add_polygon(box(-20, -20, 20, 20), layer=LAYER)
    circle = gf.Component()
    circle.add_polygon(arc((0, 20), 8, 0, 360, 64)[:-1], layer=LAYER)
    return gf.boolean(square, circle, "not", layer=LAYER)


intended = merged(ground_from_shapes())
assert (merged(ground_from_points(CLEARANCE)) ^ intended).is_empty()  # right direction: same shape
assert round(area_um2(merged(ground_from_points(CLEARANCE[::-1]))), 3) == 1600  # the clearance is gone
assert round(area_um2(intended), 3) == 1499.632
```

**如何檢查。** 方向錯誤的多邊形沒有任何有效性檢查看得到的缺陷；只有和預期形狀比較才找得到。

```python
reversed_report = construction_report(ground_from_points(CLEARANCE[::-1]), intended={LAYER: intended})
assert any("differs from the intended shape" in defect for defect in reversed_report[LAYER].defects)
```
