---
title: "伴隨圖層出自同一來源"
sidebar: development
---

本 PDK 中的導體最多以三個圖層描述：你繪製的金屬（`DRAW`）、在接地面上清出它周圍空間的接地光罩（`GROUND_MASK`），以及移除金屬處的蝕刻（`ETCH`）。製程堆疊由蝕刻推導金屬，即整個區域減去 `ETCH − DRAW`。SCGSim 由光罩推導金屬，即接地面減去 `GROUND_MASK`，再加上繪製的走線。兩種推導必須得到相同的金屬。圖層清單請見[圖層](../start/layers.qmd)。

本頁範例可以單獨執行，依序執行。它們共用以下設定。

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout import add_etch_for_component
from orcapen_sc_pdk.tech import LAYER

activate()
DRAW, MASK, ETCH = LAYER.D0_TOP_M1_DRAW, LAYER.D0_TOP_GROUND_MASK, LAYER.D0_TOP_M1_ETCH


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def metal_mismatch(component):
    """Where the etch-derived metal and the mask-derived metal disagree, in DBU."""
    draw = component.get_region(DRAW, merge=True)
    etch = component.get_region(ETCH, merge=True)
    mask = component.get_region(MASK, merge=True)
    plane = gf.kdb.Region(component.dbbox().to_itype(component.kcl.dbu))
    metal_from_etch = plane - (etch - draw)  # fabrication stack: domain − (ETCH − DRAW)
    metal_from_mask = (plane - mask) + draw  # SCGSim: plane − GROUND_MASK, plus the drawn traces
    return metal_from_etch ^ metal_from_mask
```

## R15. 光罩以金屬的來源繪製，蝕刻由兩者推導 {#r15}

**規則。** 以與金屬相同的錨點與尺寸繪製接地光罩，把每個清空區域（例如切割道）都放進光罩，並以 `add_etch_for_component` 推導蝕刻；它設定 `ETCH = GROUND_MASK − DRAW`。

手繪的蝕刻是第三份獨立的描述，沒有任何東西讓它與光罩保持一致。`sample_small_airbridge_chip` 在蝕刻圖層上有一個 2300 × 1000 µm 的切割框，接地光罩上卻沒有，兩種推導因此相差約 320,000 µm²（[#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58)，A6，於 [#61](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/pull/61) 修正）。對佈線而言，GDSFactory 的 cross-section 會由同一條路徑畫出金屬與它的光罩；請見[橫截面](../public-pdk-examples/cross-sections.qmd)。

![**問題。** 一塊焊墊（青綠色，`DRAW`）與它的接地淨空區（`GROUND_MASK`，灰色，此處位於琥珀色的 `ETCH` 之下），以及只畫在蝕刻圖層上的切割框，蝕刻是手繪的。紅色標出由蝕刻推導與由光罩推導的金屬不一致之處：整個切割框。](../_static/images/contributing/r15-problem.svg)

![**結果。** 切割框畫在光罩上，蝕刻由光罩與金屬推導：兩種推導處處一致。](../_static/images/contributing/r15-result.svg)

```python
PAD, CLEARANCE = (-50, -10, 50, 10), (-70, -30, 70, 30)


def frame():
    """A 10 µm dicing street around a 200 × 100 µm chip, as one region."""
    c = gf.Component()
    c.add_polygon(box(-100, -50, 100, 50), layer=MASK)
    outer = c.get_region(MASK)
    return outer - outer.sized(-gf.kcl.to_dbu(10))


def chip_with_hand_drawn_etch():  # don't: the frame is only on the etch
    c = gf.Component()
    c.add_polygon(box(*PAD), layer=DRAW)
    c.add_polygon(box(*CLEARANCE), layer=MASK)
    clearance_etch = gf.kdb.Region(gf.kdb.DBox(*CLEARANCE).to_itype(gf.kcl.dbu))
    c.add_polygon(clearance_etch - c.get_region(DRAW), layer=ETCH)
    c.add_polygon(frame(), layer=ETCH)
    return c


def chip_with_derived_etch():  # do: the frame is on the mask, the etch is derived
    c = gf.Component()
    c.add_polygon(box(*PAD), layer=DRAW)
    c.add_polygon(box(*CLEARANCE), layer=MASK)
    c.add_polygon(frame(), layer=MASK)
    return add_etch_for_component(c, draw_layer=DRAW, mask_layer=MASK, etch_layer=ETCH)


assert round(metal_mismatch(chip_with_hand_drawn_etch()).area() * gf.kcl.dbu**2) == 5600  # the frame
assert metal_mismatch(chip_with_derived_etch()).is_empty()
```

**如何檢查。** 在 cell 的測試中，於 cell 的範圍內計算兩種推導，並斷言它們的 XOR 為空，就像上面的 `metal_mismatch`，以及 `tests/test_idc_airbridge_geometry.py` 對 airbridge 晶片所做的那樣。
