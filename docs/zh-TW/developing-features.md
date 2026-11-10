---
title: "參與貢獻"
sidebar: development
---

透過[公開儲存庫](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk)貢獻可重複利用的元件、製程紀錄、範例或文件。請從變更所影響的 PDK 部分著手。

## 建立開發工作目錄

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12
```

這會安裝 PDK 與開發工具 pytest、Ruff。請執行 `uv run python --version` 確認 Python 版本。若要設定檢視工具，請參閱[入門的元件預覽教學](start/preview-cells.qmd)。文件相依套件與預覽方式請見[文件與網站](docs-publishing.md)。

若 GDSFactory+ 擴充套件在 `pyproject.toml` 或 `uv.lock` 加入本機環境設定，請將這些變更保留在本機工作目錄。

## 為新元件加入預覽 {#預覽元件}

使用方式與 KLayout 設定請見[預覽元件](start/preview-cells.qmd)。新增元件模組時，在檔案末尾加入以下區塊，讓使用者能直接執行檔案並預覽指定的元件。

```python
if __name__ == "__main__":
    # Imported here because orcapen_sc_pdk.pdk imports this module.
    from orcapen_sc_pdk.preview import show

    show(my_cell)
```

## 讓變更聚焦

- 在 OrcaPen 放置可重複利用的佈局與製程定義。
- 使用 GDSFactory 組合元件與佈線。
- cell 一律直接以 `@gf.cell` 裝飾，GDSFactory+ 只辨識這種寫法。含曲線的 cell 接收 `curve_sampling: CurveSampling = FABRICATION`，並傳給巢狀元件與曲線 helper；詳見[曲線取樣](../usage/curve-sampling.md)。
- 使用 SCGSim 準備模擬、整合求解器並分析回傳結果。
- 將私人佈局、參數與執行目錄保留在使用端專案。

新增介面前，先檢查相關既有原始碼與範例。將相關文件放在描述其公開行為的位置。

## 建構 cell 幾何

cell 正確，是指它的多邊形就是你想畫的形狀。以下規則說明如何建構出這樣的幾何、如何檢查，以及 cell 在加入 Library 之前可以放在哪裡。每條建構規則都來自實測到的失敗案例。審查者會依這些規則檢查 cell。

下列範例以已安裝的 GDSFactory 執行，並共用一個 helper：它像光罩寫入器一樣合併一個圖層，並回報合併後剩下的內容。GDS 不儲存孔洞，所以合併後區域中的孔洞會以切割線的形式畫出來。

```python
import math

import gdsfactory as gf
from kfactory import kdb
from orcapen_sc_pdk import activate

activate()
LAYER = (1, 0)


def report(component, layer=LAYER):
    """Polygons, holes, shortest edge (DBU) and smallest interior angle after merging."""
    index = component.kcl.layout.layer(*layer)
    region = kdb.Region(component.begin_shapes_rec(index)).merged()
    edges, angles = [], []
    for polygon in region.each():
        for i in range(-1, polygon.holes()):  # -1 is the outer contour
            points = list(polygon.each_point_hull() if i < 0 else polygon.each_point_hole(i))
            for before, here, after in zip(points[-1:] + points[:-1], points, points[1:] + points[:1]):
                incoming = (here.x - before.x, here.y - before.y)
                outgoing = (after.x - here.x, after.y - here.y)
                edges.append(math.hypot(*outgoing))
                turn = math.atan2(
                    incoming[0] * outgoing[1] - incoming[1] * outgoing[0],
                    incoming[0] * outgoing[0] + incoming[1] * outgoing[1],
                )
                angles.append(180 + math.degrees(turn))  # KLayout keeps material on the right
    return {
        "polygons": region.count(),
        "holes": sum(polygon.holes() for polygon in region.each()),
        "min_edge_dbu": round(min(edges), 1),
        "min_angle_deg": round(min(angles), 1),
    }
```

### 建構規則

**R1. 一個剛性形狀在同一個座標系中繪製，然後旋轉，再移動。** 剛性形狀的每個部分都在單一區域座標系中繪製，共用邊使用相同座標。接著依序執行 `ref.drotate(angle)`、`ref.dmove(offset)`。若分別旋轉與移動各部分，每條共用邊會各自被捨入，導體可能因此斷開。依尺寸不同，共用邊會把導體切成兩個多邊形（如下方 315° 與 17.3°），或留下 1 DBU 的邊。

```python
PARTS = [(0, 9.3643, 3.3), (9.3643, 16.7689, 6.1)]  # x0, x1, height; share x = 9.3643


def rect(x0, x1, height):
    return [(x0, 0), (x1, 0), (x1, height), (x0, height)]


def separately(angle):  # don't: each part gets its own rotation and move
    c, t = gf.Component(), math.radians(angle)
    for x0, x1, height in PARTS:
        part = gf.Component()
        part.add_polygon(rect(0, x1 - x0, height), layer=LAYER)
        ref = c << part
        ref.drotate(angle)
        ref.dmove((x0 * math.cos(t), x0 * math.sin(t)))
    return c


def together(angle):  # do: one frame, then rotate, then move
    shape = gf.Component()
    for part in PARTS:
        shape.add_polygon(rect(*part), layer=LAYER)
    c = gf.Component()
    ref = c << shape
    ref.drotate(angle)
    ref.dmove((5, 5))
    return c


for angle in (315, 17.3):
    print(angle, "separately", report(separately(angle)))
    print(angle, "together  ", report(together(angle)))
```

由單一寬度的直線導體構成的部分是「多個部分」的例外：同寬度的走線及其延伸段是同一個輪廓，不要拆成沿著本應共用的邊相接的矩形。金屬與其周圍的遮罩（例如 CPW 遮罩）共用路徑與截面尺寸、區域錨點與端點定義。遮罩延伸超出金屬的地方，請從這些錨點撰寫遮罩的整條邊，並讓金屬端點與其 port 維持原位。

**R2. 只有要把東西放到圓上時，才先移動再旋轉。** `drotate` 繞著父層級的原點旋轉，而不是繞著該部分旋轉。要做極座標放置時才先移動再旋轉，並用註解說明。若要讓某個部分原地轉動，請傳入它的中心。

```python
rect_cell = gf.components.rectangle(size=(4, 2), layer=LAYER)
c = gf.Component()
ref = c << rect_cell
ref.dmove((10, 0))
ref.drotate(90)  # polar placement: the part swings to x=-2..0, y=10..14
print(ref.dbbox())

c = gf.Component()
ref = c << rect_cell
ref.dmove((10, 0))
ref.drotate(90, center=ref.dcenter)  # in place: the part stays around (12, 1)
print(ref.dbbox())
```

**R3. 旋轉與鏡射 reference，不要動共用的 cell。** 由 `@gf.cell` 工廠建立的 cell 會被快取，並由所有呼叫者共用。請對 `c << cell` 取得的 reference 做轉換。GDSFactory 會拒絕修改被快取的 cell 本身；若有 cell 沒有拒絕，它就會對所有使用者一起改變。

```python
try:
    rect_cell.drotate(30)  # don't: rect_cell is the cached cell
except RuntimeError as error:
    print("refused:", error)
```

**R4. 先鏡射再旋轉，並驗證一個標記 port。** 鏡射與旋轉不可交換：在 30° 時，兩種順序的結果相差 60°。請刻意選擇順序，在註解中寫明鏡射軸，並在組合後檢查一個標記 port 的方向。

```python
marker = gf.Component()
marker.add_polygon([(0, 0), (4, 0), (0, 2)], layer=LAYER)
marker.add_port("m", center=(4, 0), width=1, orientation=0, layer=LAYER)

c = gf.Component()
ref = c << marker
ref.dmirror_y()  # mirror across the x axis
ref.drotate(30)
print("mirror, rotate:", ref.ports["m"].orientation)  # 30

c = gf.Component()
ref = c << marker
ref.drotate(30)
ref.dmirror_y()
print("rotate, mirror:", ref.ports["m"].orientation)  # 330, not 30
```

**R5. 邊與曲線相接時，讓邊延伸進本體。** 把直邊延伸進本體，或重用本體自己的頂點。不要在同一個半徑上再取樣第二條弧來「對接」第一條，也不要把它移動幾奈米：同一條理想曲線的兩次取樣在格點上不會重合，兩者之間的細縫會變成孔洞。必須共用一條弧的接合處，要使用相同的取樣角度與相同的錨點。

```python
def arc(radius, n, start=0.0, stop=360.0, closed=False):
    step = (stop - start) / n
    angles = [math.radians(start + i * step) for i in range(n + closed)]
    return [(radius * math.cos(a), radius * math.sin(a)) for a in angles]


def lead_on_disk(disk_points, lead_ends_on_arc_points=None):
    c = gf.Component()
    c.add_polygon(arc(50, disk_points), layer=LAYER)
    if lead_ends_on_arc_points:  # don't: a second sampling of the same circle
        landing = arc(50, lead_ends_on_arc_points, -20, 20, closed=True)
        c.add_polygon([(80, -8), (80, 8)] + landing[::-1], layer=LAYER)
    else:  # do: the lead's sides run straight into the disk
        c.add_polygon([(80, -8), (80, 8), (40, 8), (40, -8)], layer=LAYER)
    return c


print("separate arc:", report(lead_on_disk(128, 100)))
print("into the body:", report(lead_on_disk(128)))
```

**R6. 先聯集，只圓角一次；要保留方形端點，就先延伸再裁切。** 導體的所有部分都聯集之後才圓角。先對某個部分圓角、再加入其他幾何，會在圓角與新部分相接處留下凹痕。要保留方形端點，請把輪廓延伸超過端點，再裁切回來。不要用圓形視窗限制圓角。disk qubit 的 claw 尖刺，就是因為先對 claw 圓角、再把錐形聯集上去。

```python
dbu = 1000  # DBU per micrometre in this PDK


def box(x0, y0, x1, y1):
    return kdb.Region(kdb.Box(x0 * dbu, y0 * dbu, x1 * dbu, y1 * dbu))


def rounded(region, radius=3):
    return region.rounded_corners(radius * dbu, radius * dbu, 64)


left, right = box(0, 0, 20, 10), box(20, 0, 30, 10)
dont = (rounded(left) + rounded(right)).merged()  # round, then add
do = rounded((left + right).merged())             # union, then round once
print("area that differs, um2:", (dont ^ do).area() / dbu**2)  # dents at x = 20
```

**R7. 只有在建構無法做到穩健時，才加入輸入檢查。** 請先嘗試修正建構方式。只對幾何無法支援的輸入加入檢查，為它寫錯誤測試，並在 cell 的文件中說明支援範圍。不要用參數限制來掩蓋可以修正的建構問題：單單限制角度，claw 仍然留下 16–93 nm 的錯位。也不要事後悄悄加入重疊、全域貼齊格點、簡化或修補幾何來掩蓋症狀。更小的 DBU 或圓上更多的取樣點，同樣無法解決建構上的成因：上方 R5 的接合即使取樣點增為八倍仍會失敗。

```python
def span_deg_checked(span_deg):
    if not 0 < span_deg <= 60:  # do: reject what the construction cannot make
        raise ValueError(f"span_deg must be in (0, 60], got {span_deg}")
    return span_deg  # don't: min(span_deg, 40), which changes the design silently


try:
    span_deg_checked(61)
except ValueError as error:  # a test asserts this error with pytest.raises
    print("rejected:", error)

print("1024 points:", report(lead_on_disk(1024, 800)))  # holes remain
```

**R8. 每次建構後執行建構檢查。** 「看起來沒問題」不是證據。請在測試中以預設值與支援範圍的各個角落建構 cell，然後斷言沒有非預期的孔洞、沒有短於 2 DBU 的邊，並印出最小內角。內角目前沒有門檻，所以只回報、不斷言。每個刻意存在的孔洞都要明確列出。這項檢查在預設的 disk qubit 上約需 0.02 秒，並找出了上述兩個缺陷。

這個範例是零孔洞的情況：cell 沒有刻意存在的孔洞。

```python
component = together(315)
result = report(component)
intended_holes = 0  # name each cut-out you drew on purpose, per layer
assert result["holes"] == intended_holes
assert result["min_edge_dbu"] >= 2
print("min interior angle (reported only):", result["min_angle_deg"])
```

當 cell 有刻意存在的孔洞時，測試要檢查孔洞的位置與形狀，而不只是數量：橫向移動的切口數量不變。請把合併後的孔洞與你預期的切口相比。

```python
def holes_of(component, layer=LAYER):
    index = component.kcl.layout.layer(*layer)
    region = kdb.Region(component.begin_shapes_rec(index)).merged()
    return kdb.Region(
        [kdb.Polygon(list(p.each_point_hole(i))) for p in region.each() for i in range(p.holes())]
    )


def plate_with_cutout(x0):  # a 10 um plate with one 1 um square cut-out at x0..x0+1, y 2..3
    c = gf.Component()
    for x_min, y_min, x_max, y_max in [(0, 0, 10, 2), (0, 3, 10, 10), (0, 2, x0, 3), (x0 + 1, 2, 10, 3)]:
        c.add_polygon([(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)], layer=LAYER)
    return c


expected = kdb.Region(kdb.Box(2000, 2000, 3000, 3000))  # the cut-out you meant, in DBU
assert (holes_of(plate_with_cutout(2)) ^ expected).is_empty()  # right place, right shape
print("cut-out moved right, differing polygons:", (holes_of(plate_with_cutout(6)) ^ expected).count())
```

### Helper 與結構

這些規則由 PDK 維護者決定。不論 cell 檔案多長，它們讓結構容易審查，也讓一次修正能涵蓋所有共用該部件的 cell。

**H1. 先重用，再自己寫。** 請依下列順序使用現有的內容繪製：

1. `orcapen_sc_pdk.helpers`，例如以 `polar_point` 與 `rotate_point` 取代行內的 `cos` 與 `sin`，以及 `merge_component_layers`、`add_etch_for_component`。
2. PDK 的 cell 與基本元件，位於 `orcapen_sc_pdk/cells/layout/primitives.py`（`bend_euler`、`rounded_rectangle`、`wire_corner` 等）；請見[共用版圖基本元件](public-pdk-examples/shared-primitives.md)。
3. 公開的 GDSFactory API。

現有函式不適用時，請在 PR 中點名該函式並說明原因。

**H2. 新增函式須先取得核准。** 任何不是 `@gf.cell` 元件的新函式，無論是 cell 檔案私有的，或放在 `helpers/` 下共用的，都必須在撰寫前於 Issue 或 PR 取得 PDK 維護者的核准。PR 要列出每個新函式，以及現有函式為何不適用。既有的私有函式，會在其 cell 下次改寫時一併審查。

**H3. 結構比長度重要。** cell 檔案長一點沒有問題。可獨立重用、預覽或模擬的部件，要成為自己的 `@gf.cell`；若其他 cell 也會用到，就放在自己的模組。cell 本體依物理部件的順序撰寫，每個部件以一行簡短的註解標題開頭。

### 三種檢查

這些檢查回答不同的問題、有不同的負責方，也觸及不同的使用者。請把它們分開看待：其中一種通過，不代表其他種也通過。

| 種類 | 問題 | 負責方 | 適用範圍 |
|---|---|---|---|
| 建構檢查 | 程式碼畫出的是不是它想畫的？沒有非預期的孔洞、沒有短於 2 DBU 的邊、回報最小內角 | 本 PDK，在其測試中 | 在每個 PDK cell 的測試中執行，從 disk flip-chip qubit 開始；其他 cell 隨測試加入而補上。其他佈局可自行選用 |
| 製程設計規則（DRC） | 製程做得出來嗎？每個圖層的寬度、間距與包覆 | 本 PDK | 自願採用。使用端可以採用、修改或忽略 |
| 模擬檢查 | 求解器能建模嗎？ | [SCGSim](https://github.com/NCUPHY-LTLab/scgsim) | 由 SCGSim 定義與執行，不屬於本 PDK |

PDK 的使用端不必遵循製程規則。

### 記錄製程規則

製程規則不自行發明。規則必須附有 PDK 維護者提供的來源才能加入，且每條規則記錄：

- **來源**：數值出自何處。
- **圖層**：適用的圖層或圖層組合。
- **數值**：數字與單位。
- **狀態**：`proposed` 或 `adopted`。

列出製程規則的頁面，以及檢查這些規則的程式碼，會與第一條有來源的規則一起加入。

### 候選 cell

本儲存庫的 `develop` 分支不放候選 cell。使用端會固定使用這個分支，GDSFactory+ 也會列出其中的 cell，所以放在這裡的候選 cell 會變成別人可以依賴的東西。候選 cell 放在它的 Issue 分支上。由 repository 擁有者決定是否把它合併到個人分支來預覽。這裡的個人分支是公開的，所以含有私人設計的候選 cell 要改從私人佈局儲存庫開始。

## 提交變更

在提取要求中說明變更的行為、受影響的公開介面及已執行的檢查。已儲存的科學結果應與原始模型及執行環境對應；修改教學不會重新執行結果。

套件角色請見[工作區與相關套件](home/ecosystem-workspace.md)；來源與執行期的界線請見[SCGSim 整合](features/scgsim-integration.md)；筆記本配對與部署請見[文件與網站](docs-publishing.md)。
