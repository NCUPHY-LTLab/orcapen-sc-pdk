---
title: "格點與有效多邊形"
sidebar: development
page-navigation: true
---

GDS 以資料庫單位（database unit，DBU）的整數儲存每個座標。本 PDK 的 1 DBU 是 1 nm，所以你畫的每個頂點在儲存時都會捨入到 1 nm 格點。以下三條規則讓這個捨入不會改變導體（一塊應該電性連續的金屬）：它的各部件在哪裡相接、它的輪廓是不是有效的多邊形，以及它是不是一整塊。

以 `uv run pytest tests/test_docs_construction_examples.py -k grid-and-polygons` 執行本頁範例。範例依序執行，共用以下設定。測試會把 `tests/` 加入匯入路徑，`geometry_checks` 就在那裡。

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate

activate()
LAYER = (1, 0)


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def merged(component):
    """The layer as a mask writer sees it: overlapping polygons joined into one."""
    return component.get_region(LAYER, merge=True)
```

## R1. 每個長度與位置都放在 1 nm 格點上 {#r1}

**規則。** 你用來繪製的每個長度與位置都是整數個奈米，讓應該相接的兩個部件落在同一個格點上。

不在格點上的值會在使用的地方被捨入。多個不在格點上的值相加後再捨入，和各自捨入後再相加的結果不同；所以放在 `pad_length + lead_length` 的部件，和從 `pad_length` 起延伸自身 `lead_length` 的導線，可能相差 1 nm。這個間隙會把導體切成兩塊。Purcell 讀取 cell 中 IDC 指狀電極與錐形段之間的十條 1 nm 狹縫，也是同一個原因造成的，當時指狀電極長度是 59.92476 µm（[#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58)，A1）。

![**問題。** 一塊焊墊、一段導線與第二塊焊墊，各自放在前面那些不在格點上的長度（10.0004 µm 與 5.0004 µm）之和。每個合併後的多邊形各有一種顏色：第二塊焊墊是另一個多邊形。放大圖顯示導線末端的 1 nm 間隙。](../_static/images/contributing/zh-TW/r1-problem.svg)

![**結果。** 同樣的串接改用格點上的長度（10 µm 與 5 µm），成為一個多邊形。放大圖顯示同一個位置。](../_static/images/contributing/zh-TW/r1-result.svg)

```python
def pad_lead_pad(pad_length, lead_length):
    """A 10 µm pad, a 4 µm lead and a second pad, each placed at the sum of the lengths before it."""
    c = gf.Component()
    pad = gf.components.rectangle(size=(pad_length, 10), layer=LAYER)
    lead = gf.components.rectangle(size=(lead_length, 4), layer=LAYER)
    c << pad
    (c << lead).dmove((pad_length, 3))
    (c << pad).dmove((pad_length + lead_length, 0))
    return c


off_grid = pad_lead_pad(10.0004, 5.0004)
on_grid = pad_lead_pad(10.0, 5.0)
assert merged(off_grid).count() == 2  # the second pad is cut off by a 1 nm gap
assert merged(on_grid).count() == 1
```

**如何檢查。** cell 以指出參數名稱的錯誤拒絕不在格點上的長度或位置參數（[R16](input-checks.md#r16)）。`gf.snap.is_on_grid(value)` 可判斷一個值是否在格點上。建構檢查接著計算每個導體的多邊形數量（[R18](construction-checks.md)）。

```python
assert not gf.snap.is_on_grid(10.0004)
assert gf.snap.is_on_grid(10.0)
```

由三角函數或曲線取樣算出的值，本來就不在格點上。它們不會被拒絕；後續頁面的規則會讓它們不至於把導體切開。

## R2. 每個多邊形都畫成有效的：不自我相交，也不自我接觸 {#r2}

**規則。** 每個多邊形的輪廓只繞一圈，不與自己交叉或接觸；同一個導體的各部件以實際的寬度重疊，絕不只在一個點上相接。

網格產生器與布林運算引擎需要有效的多邊形。同一個導體的兩個部件若只在角落相接，合併後會成為一個兩次經過同一頂點的輪廓，這不是有效的多邊形。順序錯誤的點列則會與自己交叉。`disk_flip_chip_qubit` 的接地輪廓曾經自我交叉，控制晶片上第一個交叉點在 (−409.839, 423.274) µm，量子位元晶片上在 (−500, 452.314) µm（[#47](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/47)）。

![**問題。** 兩塊只在角落相接的焊墊。合併後的輪廓兩次經過 (10, 10) µm，放大圖標出了這一點。](../_static/images/contributing/zh-TW/r2-problem.svg)

![**結果。** 同樣的焊墊重疊 1 µm：一個有效的輪廓。放大圖顯示同一個位置。](../_static/images/contributing/zh-TW/r2-result.svg)

```python
def two_pads(overlap):
    """Two 10 µm pads, the second shifted so that their corners overlap by `overlap` µm."""
    c = gf.Component()
    c.add_polygon(box(0, 0, 10, 10), layer=LAYER)
    c.add_polygon(box(10 - overlap, 10 - overlap, 20, 20), layer=LAYER)
    return c


touching = two_pads(0)
overlapping = two_pads(1)
```

**如何檢查。** `tests/geometry_checks.py` 的 `construction_report` 以 Python 幾何函式庫 Shapely 檢查每個繪製的多邊形與每個合併後的多邊形，並指出缺陷與其位置（[R18](construction-checks.md)）。

```python
from geometry_checks import construction_report  # tests/geometry_checks.py

assert "merged: Ring Self-intersection[10000 10000]" in construction_report(touching)[LAYER].defects
assert construction_report(overlapping)[LAYER].defects == ()
```

報告中的位置以 DBU 表示：`[10000 10000]` 就是 (10, 10) µm。

## R3. 每個導體都自成一個連通的多邊形 {#r3}

**規則。** 每個導體靠自己的建構就是一個多邊形，而不是要等另一個部件加上去之後才是。

依賴鄰近部件才能連在一起的部件，在鄰近部件移動、改變或被省略時就會散開，合併後的圖層會有比導體更多的塊數。Purcell IDC 的梳狀電極原本沒有自己的連接條：它的指狀電極只透過零寬度的線段相連，要靠錐形段把它們接起來（[#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58)，A1）。修正方式是讓每個梳狀電極都有一條主幹。

![**問題。** 沒有主幹、由五根指狀電極組成的梳狀電極單獨建構：五個多邊形。](../_static/images/contributing/zh-TW/r3-problem.svg)

![**結果。** 同樣的梳狀電極加上 4 µm 的主幹：一個多邊形。](../_static/images/contributing/zh-TW/r3-result.svg)

```python
def comb(spine):
    """Five 3 µm fingers at a 6 µm pitch, 30 µm long, with or without a spine under them."""
    c = gf.Component()
    for finger in range(5):
        c.add_polygon(box(6 * finger, 0, 6 * finger + 3, 30), layer=LAYER)
    if spine:
        c.add_polygon(box(0, -4, 27, 0), layer=LAYER)
    return c


assert merged(comb(spine=False)).count() == 5
assert merged(comb(spine=True)).count() == 1
```

**如何檢查。** 單獨建構該導體並計算合併後的多邊形數量，或把每個圖層的導體數量傳給 `construction_report`（[R18](construction-checks.md)）。

```python
report = construction_report(comb(spine=False), conductors={LAYER: 1})[LAYER]
assert "merged: 5 polygons for 1 conductor(s)" in report.defects
assert construction_report(comb(spine=True), conductors={LAYER: 1})[LAYER].defects == ()
```
