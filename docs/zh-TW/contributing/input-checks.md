---
title: "輸入檢查"
sidebar: development
---

輸入檢查讓 cell 拒絕某個參數值，而不是把它畫出來。只有在幾何無法支援該值、而且建構方式已經盡可能穩健之後，它才是正確的工具。R7 分成四個部分。

本頁範例可以單獨執行，依序執行。它們共用以下設定。

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point
from orcapen_sc_pdk.pdk import PDK

activate()
LAYER = (1, 0)
```

## R7a. 先修正建構方式，再限制輸入 {#r7a}

**規則。** 某個參數值畫出錯誤的形狀時，先找出建構上的原因；只有在沒有任何建構方式畫得出該值時，才限制該參數。

限制會把原因藏在它允許的那些值裡。在 `disk_flip_chip_qubit` 中，把爪形電極的著陸張角限制在預設值下的 42.51°，並沒有消除爪形的尖刺與 16–93 nm 的折線；它們來自先對爪形做圓角、才加上錐形段（[#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53)，原因 2；[R6](one-outline.md#r6)）。更細的取樣或更小的資料庫單位（DBU，GDS 儲存的格點；這裡是 1 nm）也治不好建構上的原因：點數增為八倍時，[R5](curves.md#r5) 的曲線接合孔洞反而更多。

**如何檢查。** 其他頁面上的每條建構規則都說明了如何檢查它的缺陷；在加上限制之前，先在整個範圍內執行那些檢查。

## R7b. 拒絕建構方式畫不出的值，絕不夾限 {#r7b}

**規則。** 引發一個指出參數名稱與支援範圍的 `ValueError`，為這個錯誤寫測試，並在 cell 的 docstring 中寫明範圍。不要把值換成最接近的支援值。

被夾限的值畫出的是與要求不同的設計，而且沒有任何東西告訴呼叫者。

![**問題。** 要求 90° 張角的爪形（虛線），因為程式碼默默夾限張角，畫出來是 60°。](../_static/images/contributing/r7b-problem.svg)

![**結果。** 有檢查的爪形精確畫出所要求的 60°，而 90° 的要求則引發錯誤。](../_static/images/contributing/r7b-result.svg)

```python
MAX_SPAN = 60  # degrees; adjacent claws would touch beyond this


def claw_points(span):
    """An arc band from radius 100 to 120 µm, centred on 0°, `span` degrees wide."""
    steps = 32
    angles = [-span / 2 + span * i / steps for i in range(steps + 1)]
    return [polar_point(120, a) for a in angles] + [polar_point(100, a) for a in reversed(angles)]


def claw_clamped(span):  # don't: draws 60° when asked for 90°
    c = gf.Component()
    c.add_polygon(claw_points(min(span, MAX_SPAN)), layer=LAYER)
    return c


def claw_checked(span):  # do: refuse what the construction cannot draw
    if not 0 < span <= MAX_SPAN:
        raise ValueError(f"span must be in (0, {MAX_SPAN}] degrees, got {span}")
    c = gf.Component()
    c.add_polygon(claw_points(span), layer=LAYER)
    return c


assert claw_clamped(90).dbbox() == claw_checked(60).dbbox()  # the 90° request drew the 60° claw
with pytest.raises(ValueError, match="span must be in"):
    claw_checked(90)
```

實際的 cell 也是這麼做的。`disk_flip_chip_qubit` 會拒絕它的爪形無法避開的接面角度：

```python
with pytest.raises(ValueError, match="junction and open lead angles must be 45° \\+ k·90°"):
    PDK.get_component("disk_flip_chip_qubit", junction_angle=0.0)
```

**如何檢查。** cell 的測試以 `pytest.raises` 斷言這個錯誤與訊息，如上所示，並對範圍兩端外側各取一個值。

## R7c. 拒絕不在格點上的輸入 {#r7c}

**規則。** 直接決定幾何的長度或位置參數必須是整數個奈米；不在格點上的值會引發指出參數名稱的 `ValueError`。

不在格點上的值會在使用的地方被捨入，所以應該相接的兩個部件可能相差 1 nm（[R9](grid-and-polygons.md#r9)）。這項檢查適用於呼叫者傳入的值，不適用於由三角函數或曲線取樣算出、本來就不在格點上的值（[#62](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/62)）。Purcell 讀取 cell 會拒絕曾經留下 1 nm 狹縫的 IDC 指狀電極長度（[#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58)，A1）：

```python
PURCELL = "capacitive_coupling_intrinsic_individual_purcell_filter_readout_resonators"
with pytest.raises(ValueError, match="idc_finger_length must be aligned to the active manufacturing grid"):
    PDK.get_component(PURCELL, idc_finger_length=59.92476)
```

**如何檢查。** 由 `gf.snap.is_on_grid(value)` 判斷；cell 的測試對每個受檢查的參數，各以一個不在格點上的值斷言這個錯誤。

## R7d. 不要掩蓋症狀 {#r7d}

**規則。** 不要在事後掩蓋建構缺陷：不為了補上間隙而加入重疊、不做全域對齊格點、不在建構完成後簡化或修補幾何。

修補會把原因藏起來，讓每一項檢查與下一位讀者都看不到，還會在沒有人想改的地方改變形狀。屬於設計一部分的重疊則不同：SCGSim 在 #58 回報的 1 nm 薄片重疊是刻意的，也是受支援的（[#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58)，A7 已撤回）。判斷依據是理由：為了掩蓋間隙而存在的重疊才是缺陷。

**如何檢查。** 審查差異：修正會改變造成缺陷的建構方式，而發現該缺陷的建構檢查隨後通過，過程中沒有加入任何重疊、對齊格點或修補步驟。
