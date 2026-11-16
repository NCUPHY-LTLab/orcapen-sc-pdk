---
title: "什麼是 cell"
sidebar: development
---

cell 是以 `@gf.cell` 裝飾、由參數建出一個元件的函式。GDSFactory 會快取它，GDSFactory+ 會列出它，其他 cell 以 reference 擺放它；reference 是共用 cell 的一次擺放，有自己的位置、旋轉與鏡射。以下四條規則說明什麼會成為 cell、用什麼來建構它，以及它的程式碼如何安排。這些規則由 PDK 維護者訂定；審查者會先依它們檢查新的 cell，再依[建構規則](rules.md)檢查。

## H1. 先重用，再自己寫 {#h1}

**規則。** 依下列順序，使用已有的內容建構；若有既有函式不適用，請在提取要求中點名並說明原因。

1. **PDK 的 cell 與基本元件**：已註冊的 cell，以及 `orcapen_sc_pdk/cells/layout/primitives.py`（`bend_euler`、`rounded_rectangle`、`wire_corner` 等）；請見[共用版圖基本元件](../public-pdk-examples/shared-primitives.md)。
2. **GDSFactory 公開 API**：`gf.components`、`gf.path`、`gf.cross_section`、`Component.get_region`、`gf.boolean` 與 `connect`。KLayout 的幾何型別請用 `gf.kdb`，格點請用 `gf.kcl.dbu` 與 `gf.kcl.to_dbu`，不要自行匯入 KLayout 或 kfactory。
3. **PDK helper**：`orcapen_sc_pdk.helpers.layout` 與 `orcapen_sc_pdk.curve_sampling`。例如以 `polar_point` 與 `rotate_point` 取代行內的 `cos` 與 `sin`。

以下匯入路徑可以照寫使用：

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk.curve_sampling import FABRICATION, circle_segments
from orcapen_sc_pdk.helpers.layout import add_etch_for_component, merge_component_layers
from orcapen_sc_pdk.helpers.layout.geometry import polar_point, rotate_point

assert polar_point(10, 90) == pytest.approx((0, 10))  # radius, angle in degrees
assert rotate_point((10, 0), 90) == pytest.approx((0, 10))  # about the origin
assert gf.kcl.to_dbu(1.5) == 1500  # 1 DBU is 1 nm
assert circle_segments(50, FABRICATION) > 0  # points per circle for this radius and sampling
```

## H2. 新的 helper 函式列在 Issue 上，一次核准 {#h2}

**規則。** 每個不是 `@gf.cell` 的新函式，都在 Issue 上列出一次，由 PDK 維護者在你撰寫之前一次核准整份清單。

清單對每個函式說明它做什麼，以及為何沒有既有函式適用（H1）。不論函式只屬於某個 cell 檔案，或放在 `orcapen_sc_pdk/helpers/` 下共用，都適用這條規則。有兩種函式不需要核准：

- 只包一個運算式、僅在檔案內使用的小型包裝函式；
- 測試用的 helper。

既有的私有函式，會在其 cell 下次改寫時一併審查。

## H3. 部件本身就是一個元件時，才成為 cell {#h3}

**規則。** 部件本身就是一個元件時，把它寫成 `@gf.cell`；當它的形狀或位置來自宿主元件時，把它寫成套用在宿主上的 helper 函式。

部件本身就是一個元件，是指：

- 它的形狀來自它自己的參數，而不是來自它所附著的元件；
- 它有供其他部件連接的 port；
- 它可以作為該元件單獨製作與模擬，例如彎管、launcher、交指電容或共振器。

因此彎管這類佈線部件是 cell：它們可以單獨存在，也帶有 port。

部件來自宿主，是指它在宿主的某個 port 上或沿著宿主的輪廓修改宿主，例如 CPW port 上的開路端，或畫在導體周圍的蝕刻。這樣的部件是接收宿主的 helper 函式，就像 `add_etch_for_component`。

除非 PDK 為某個 GDSFactory 元件加上了幾何或意義，否則不要把它包成 PDK 的 cell（H1）。

## H4. 結構比長度重要 {#h4}

**規則。** cell 本體依物理部件的順序撰寫，每個部件以一行簡短的註解標題開頭；cell 檔案長一點沒有問題。

讀者依部件理解 cell，所以程式碼的順序就是部件在版圖中的順序。成為 cell 的部件（H3），在其他 cell 也用到它時移到自己的模組，讓一次修正能涵蓋所有共用它的 cell。
