---
title: "曲線：接合與切割"
sidebar: development
page-navigation: true
---

GDS 中的曲線是一個多邊形：它的頂點是在理想曲線上取樣的點，以直線弦連接，每個頂點都捨入到 1 nm 格點。同一條曲線取樣兩次，就是兩個不同的多邊形。以下規則說明如何把直邊接到曲線上，以及如何切過曲線，讓兩次取樣永遠不必互相吻合。

本頁用到的名詞：

- **DBU**（資料庫單位）：GDS 儲存的整數格點；這裡 1 DBU 是 1 nm。
- **弓高**（sagitta）：弦與它所代表的圓弧之間的最大距離。對半徑 R 上張角 θ 的弦，弓高是 R·(1 − cos(θ/2))：半徑 50 µm、每圈 128 點的圓，一步約 15 nm。
- **孔洞**：合併後多邊形中被包圍的空隙。GDS 無法儲存孔洞，所以寫入器會以一條切割線把每個孔洞接到外輪廓。

以 `uv run pytest tests/test_docs_construction_examples.py -k curves` 執行本頁範例。範例依序執行，共用以下設定。測試會把 `tests/` 加入匯入路徑，`geometry_checks` 就在那裡。

```python
import math

import gdsfactory as gf
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point

activate()
LAYER = (1, 0)
RADIUS = 50  # µm


def arc(radius, start, stop, segments):
    """Points on a circle from `start` to `stop` degrees, both ends included."""
    return [polar_point(radius, start + (stop - start) * i / segments) for i in range(segments + 1)]


def disk(segments):
    return arc(RADIUS, 0, 360, segments)[:-1]


def merged(component):
    return component.get_region(LAYER, merge=True)


def sagitta(radius, step_deg):
    return radius * (1 - math.cos(math.radians(step_deg) / 2))


assert round(sagitta(RADIUS, 360 / 128) * 1000) == 15  # nm
```

## R11. 直邊與曲線相接處，讓直邊延伸進本體 {#r11}

**規則。** 把部件的直邊延伸越過曲線、進入本體（部件所接上的形狀，這裡是圓盤），或沿著接合處重用本體自己的頂點；絕不在同一半徑上取樣第二段圓弧去接第一段。

同一個圓的兩次取樣不會在格點上重合：在兩者的頂點之間，弦在弓高範圍內來回交叉，它們圍出的細長碎片在合併後成為孔洞。`disk_flip_chip_qubit` 的導線扇形原本結束在自己於圓盤半徑取樣的圓弧上，在量子位元金屬上留下 14 個孔洞；把那段圓弧縮小不到一個弓高，並不能消除它們（[#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53)，原因 1）。

![**問題。** 一條從 16 µm 張開到 ±20° 的導線，結束在自己的圓弧上（40° 內 100 步），位於每圈 128 點的圓盤半徑處。合併後的圖層沿著接合處有 8 個孔洞（標出其中一個）；放大圖拉近到看得出它的寬度。](../_static/images/contributing/zh-TW/r11-problem.svg)

![**結果。** 同樣的張開形狀，直邊繼續延伸進圓盤：沒有孔洞。放大圖顯示同一個位置。](../_static/images/contributing/zh-TW/r11-result.svg)

```python
def flared_lead(landing):
    """A lead from x = 80 µm, 16 µm wide, flaring out to the given landing points."""
    return [(80, -8), (80, 8)] + landing


def lead_on_a_second_arc(disk_segments, landing_segments):  # don't
    c = gf.Component()
    c.add_polygon(disk(disk_segments), layer=LAYER)
    landing = arc(RADIUS, -20, 20, landing_segments)
    c.add_polygon(flared_lead(landing[::-1]), layer=LAYER)
    return c


def lead_into_the_body(disk_segments):  # do: the flare's sides continue to x = 40 µm
    c = gf.Component()
    c.add_polygon(disk(disk_segments), layer=LAYER)
    top, bottom = polar_point(RADIUS, 20), polar_point(RADIUS, -20)

    def continued(outer, corner, x_end=40):
        t = (x_end - outer[0]) / (corner[0] - outer[0])
        return (x_end, outer[1] + t * (corner[1] - outer[1]))

    c.add_polygon(flared_lead([continued((80, 8), top), continued((80, -8), bottom)]), layer=LAYER)
    return c


def lead_on_the_body_vertices(disk_segments):  # do: land on the disk's own vertices
    c = gf.Component()
    points = disk(disk_segments)
    c.add_polygon(points, layer=LAYER)
    step = 360 / disk_segments
    landing = [polar_point(RADIUS, i * step) for i in range(-int(20 // step), int(20 // step) + 1)]
    c.add_polygon(flared_lead(landing[::-1]), layer=LAYER)
    return c


assert merged(lead_on_a_second_arc(128, 100)).holes().count() == 8
assert merged(lead_into_the_body(128)).holes().count() == 0
assert merged(lead_on_the_body_vertices(128)).holes().count() == 0
assert merged(lead_on_a_second_arc(1024, 800)).holes().count() == 112  # eight times the points: more holes
```

更多的點也治不好：兩段圓弧都用八倍的點數，合併後留下 112 個孔洞。公平的比較是把同一條導線以兩種方式畫出。兩者只差在兩段圓弧之間的碎片，總共 0.34 µm²：

```python
differ = merged(lead_on_a_second_arc(128, 100)) ^ merged(lead_into_the_body(128))
assert round(differ.area() * gf.kcl.dbu**2, 2) == 0.34
```

**如何檢查。** 計算合併後圖層的孔洞，並列出每一個你刻意畫的孔洞（[R18](construction-checks.md)）。

```python
from geometry_checks import construction_report  # tests/geometry_checks.py

assert construction_report(lead_on_a_second_arc(128, 100))[LAYER].holes.count() == 8
assert construction_report(lead_into_the_body(128))[LAYER].holes.is_empty()
```

## R12. 直邊或切割線跨過取樣曲線時，讓兩者共用一個頂點 {#r12}

**規則。** 直邊跨過取樣曲線的地方，讓交點成為兩個輪廓共同的頂點：取樣曲線時讓一個頂點落在交點上，並讓直邊結束在那個頂點。

若交給合併處理，交點會被計算出來並捨入到格點。當它落在曲線某個頂點的一奈米以內時，合併後的輪廓會同時保留兩者，相距 1 DBU。在 `disk_flip_chip_qubit` 中，爪形錐形段的光罩條跨過 350 µm 淨空圓的地方，接地光罩上出現 1 DBU 的邊，60 個著陸張角中有 3 個如此；著陸張角（`tc_landing_span`）是爪形錐形段與圓盤側相接的角度範圍，見[元件頁面](../public-pdk-examples/components/disk_flip_chip_qubit.qmd)（[#63](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/63)）。

![**問題。** 一條寬 14.672 µm（在格點上）的長條伸進每圈 128 點的圓盤。它的邊在距一個頂點約 0.5 nm 處跨過圓盤輪廓。放大圖聚焦在上方的交點，合併在那裡留下一條 1 DBU 的邊（已標出），網格產生器必須以同樣小的元素解析它（[R18](construction-checks.md)）。](../_static/images/contributing/zh-TW/r12-problem.svg)

![**結果。** 圓盤從交點的角度開始取樣，長條結束在那個頂點上。放大圖顯示同一個位置，沒有過短的邊。](../_static/images/contributing/zh-TW/r12-result.svg)

```python
def short_edges(component):
    """Edges of the merged layer shorter than 2 DBU."""
    return merged(component).edges().with_length(0, 2, False)


def strip_across_disk(half_width):  # don't: the merge computes the crossing
    c = gf.Component()
    c.add_polygon(disk(128), layer=LAYER)
    c.add_polygon([(0, -half_width), (80, -half_width), (80, half_width), (0, half_width)], layer=LAYER)
    return c


def strip_on_shared_vertices(half_width):  # do: the crossing is a vertex of both
    c = gf.Component()
    crossing = math.degrees(math.asin(half_width / RADIUS))
    segments = math.ceil((360 - 2 * crossing) / (360 / 128))  # about the same step as before
    body = arc(RADIUS, crossing, 360 - crossing, segments)  # starts and ends on the crossings
    c.add_polygon(body, layer=LAYER)
    top, bottom = body[0], body[-1]
    c.add_polygon([bottom, (80, bottom[1]), (80, top[1]), top], layer=LAYER)
    return c


assert short_edges(strip_across_disk(7.336)).count() == 2  # at (49.459, ±7.336) µm
assert short_edges(strip_on_shared_vertices(7.336)).count() == 0
```

`with_length(0, 2, False)` 計算長度至少 0、小於 2 DBU 的邊。[^with-length]共用頂點的建構方式在其他寬度也不會自己產生過短的邊：從 0.04 µm 到 20 µm 的 500 個格點上的半寬，一個也沒有；這項掃描在本指南的測試中執行。

[^with-length]: 三個參數都要傳。只傳兩個時，KLayout 會把 `with_length(0, 2)` 解讀為長度與 `inverse` 旗標，也就是「每一條長度不為 0 的邊」。

**如何檢查。** `construction_report` 會回報每一條短於 2 DBU 的邊及其位置（[R18](construction-checks.md)）。除了預設值，也要在切割線於頂點附近跨過曲線的參數值建構 cell。

```python
report = construction_report(strip_across_disk(7.336))[LAYER]
assert report.min_edge_dbu < 2
assert construction_report(strip_on_shared_vertices(7.336))[LAYER].min_edge_dbu >= 2
```
