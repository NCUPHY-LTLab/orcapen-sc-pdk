---
title: "建構檢查"
sidebar: development
---

「看起來沒問題」不是證據：在你檢視 cell 的尺度下，1 nm 的間隙、不到一奈米的邊，或幾平方微米的缺口都看不見。建構檢查讀取建好的 cell，判斷程式碼畫出的是不是它想畫的多邊形。它們位於 `tests/geometry_checks.py`，cell 的測試會呼叫 `construction_report`。

本頁範例可以單獨執行，依序在儲存庫根目錄以 `PYTHONPATH=tests` 執行（供 `geometry_checks` 匯入）。它們共用以下設定。

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point

from geometry_checks import MIN_EDGE_DBU, construction_report  # tests/geometry_checks.py

activate()
LAYER = (1, 0)


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def merged(component):
    return component.get_region(LAYER, merge=True)
```

## R8. 對 cell 支援的每一種建構執行建構檢查 {#r8}

**規則。** 在 cell 的測試中，以預設值、支援範圍的邊界值與其組合，並在兩種曲線取樣下建構 cell，然後斷言 `construction_report` 沒有發現缺陷：每個導體都是一個有效的多邊形、沒有短於 2 DBU 的邊、只有你刻意畫的孔洞，以及在你能寫出預期形狀的地方，形狀與預期相符。

`construction_report(component)` 把 cell 展平，並對每個圖層回報：

- 每個繪製的多邊形與合併後圖層的每個多邊形，是否與自己相交或接觸、是否有重複的頂點、是否有短於 `MIN_EDGE_DBU`（2 DBU，這裡是 2 nm）的邊，或是否往返形成尖刺或零寬度狹縫；
- 合併後圖層的孔洞，以區域表示，用來與你刻意畫的切口比較；
- 最小內角，目前只回報，沒有門檻；
- 傳入 `conductors={layer: n}` 時，若合併後的圖層不是剛好 `n` 個多邊形就列為缺陷，因此能找出散開的導體；
- 傳入 `intended={layer: region}` 時，合併後圖層與你預期形狀不同的地方（XOR）列為缺陷。不超過 2 DBU 寬的差異是格點捨入，不列入；那麼窄的間隙由多邊形數量找出。

DBU（資料庫單位）是 GDS 儲存的整數格點；本 PDK 的 1 DBU 是 1 nm。

![**問題。** 一個逐一部件做圓角的導體，因此在部件相接處有缺口。它是一個多邊形，沒有孔洞，也沒有過短的邊，所以只檢查孔洞與邊長會讓它通過。](../_static/images/contributing/r8-problem.svg)

![**結果。** 同一個導體與它的預期形狀比較。紅色標出 `construction_report` 回報的差異：那些缺口。](../_static/images/contributing/r8-result.svg)

下面兩個缺陷都能通過只檢查孔洞與邊長的檢查。第一個是被 1 nm 間隙切成兩塊的導體（[R9](grid-and-polygons.md#r9)）；第二個是 [R6](one-outline.md#r6) 中有缺口的導體。

```python
def split_conductor():
    """Two parts that share an off-grid edge at x = 9.3643 µm, each rotated by 315° and moved."""
    c = gf.Component()
    for x0, x1, height in [(0, 9.3643, 3.3), (9.3643, 16.7689, 6.1)]:
        part = gf.Component()
        part.add_polygon(box(0, 0, x1 - x0, height), layer=LAYER)
        ref = c << part
        ref.drotate(315)
        ref.dmove(polar_point(x0, 315))
    return c


def rounded(*boxes):
    c = gf.Component()
    for corners in boxes:
        c.add_polygon(box(*corners), layer=LAYER)
    radius = gf.kcl.to_dbu(3)
    return merged(c).rounded_corners(radius, radius, 64)


notched = gf.Component()
notched.add_polygon((rounded((0, 0, 20, 10)) + rounded((20, 0, 30, 10))).merged(), layer=LAYER)
meant = rounded((0, 0, 20, 10), (20, 0, 30, 10))


def holes_and_edges_pass(component):  # too weak on its own
    report = construction_report(component)[LAYER]
    return report.holes.is_empty() and report.min_edge_dbu >= MIN_EDGE_DBU


assert holes_and_edges_pass(split_conductor())
assert holes_and_edges_pass(notched)
```

加上多邊形數量與預期形狀後，報告兩個都找得到：

```python
split = construction_report(split_conductor(), conductors={LAYER: 1})[LAYER]
assert split.defects == ("merged: 2 polygons for 1 conductor(s)",)

notches = construction_report(notched, intended={LAYER: meant})[LAYER]
assert len(notches.defects) == 1 and "differs from the intended shape" in notches.defects[0]
assert round(notches.difference.area() * gf.kcl.dbu**2, 3) == 7.702  # µm²
```

### 列出每一個刻意畫的孔洞

當 cell 刻意有孔洞時，要把合併後的孔洞與你畫的切口比較，而不只是比較數量：橫向移動的切口數量不變。

```python
def plate_with_cutout(x0):
    """A 10 µm plate with one 1 µm square cut-out at x0…x0 + 1, y 2…3."""
    c = gf.Component()
    for corners in [(0, 0, 10, 2), (0, 3, 10, 10), (0, 2, x0, 3), (x0 + 1, 2, 10, 3)]:
        c.add_polygon(box(*corners), layer=LAYER)
    return c


cutout = gf.kdb.Region(gf.kdb.DBox(2, 2, 3, 3).to_itype(gf.kcl.dbu))  # the cut-out you meant
assert (construction_report(plate_with_cutout(2))[LAYER].holes ^ cutout).is_empty()
moved = construction_report(plate_with_cutout(6))[LAYER].holes
assert moved.count() == 1 and not (moved ^ cutout).is_empty()  # same count, wrong place
```

### 在 cell 的測試中

`tests/test_disk_qubit.py::test_every_polygon_is_drawn_as_meant` 就是這個模式：它以預設值與其 Issue 列出的邊界值，在兩種曲線取樣下建構 `disk_flip_chip_qubit`，並對每個圖層斷言沒有缺陷、沒有低於 2 DBU 的邊，且孔洞等於它列出的接地開口。它會印出最小內角，供提取要求參考。

**如何檢查。** 出現缺陷時測試就會失敗。沒有這種測試的 cell 就沒有建構證據；新增或修改 cell 時，請一併加上。
