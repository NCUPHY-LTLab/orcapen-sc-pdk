---
title: "什麼是 cell"
sidebar: development
page-navigation: true
---

cell 是以 `@gf.cell` 裝飾、由參數建出一個元件的函式。GDSFactory 會快取它，GDSFactory+ 會列出它，其他 cell 以 reference 擺放它；reference 是共用 cell 的一次擺放，有自己的位置、旋轉與鏡射。以下四條規則說明什麼會成為 cell、用什麼來建構它，以及它的程式碼如何安排。審查者會先依它們檢查新的 cell，再依[建構規則](rules.md)檢查。

H1、H2 與 H4 是關於程式碼與核准的規則，不涉及幾何，所以附的是表格或程式碼範例，而不是一對圖。H3 決定部件屬於哪一種，它的圖把兩種並列。

以 `uv run pytest tests/test_docs_construction_examples.py -k what-is-a-cell` 執行本頁範例。

## H1. 先重用，再自己寫 {#h1}

**規則。** 依下表的順序使用已有的內容建構；若有既有函式不適用，請在 PR 中點名並說明原因。

| 順序 | 來源 | 例如 |
|---|---|---|
| 1 | PDK 的 cell 與基本元件：已註冊的 cell，以及 `orcapen_sc_pdk/cells/layout/primitives.py`；請見[共用版圖基本元件](../public-pdk-examples/shared-primitives.md) | `bend_euler`、`rounded_rectangle`、`wire_corner` |
| 2 | GDSFactory 公開 API | `gf.components`、`gf.path`、`gf.cross_section`、`Component.get_region`、`gf.boolean`、`connect`；KLayout 的幾何型別用 `gf.kdb`，格點用 `gf.kcl.dbu` 與 `gf.kcl.to_dbu` |
| 3 | PDK helper：`orcapen_sc_pdk.helpers.layout` 與 `orcapen_sc_pdk.curve_sampling` | 以 `polar_point` 與 `rotate_point` 取代行內的 `cos` 與 `sin`；`add_etch_for_component` |

KLayout 的型別請透過 `gf.kdb` 取得，不要自行匯入 KLayout 或 kfactory。以下匯入路徑可以照寫使用：

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk.curve_sampling import FABRICATION, circle_segments
from orcapen_sc_pdk.helpers.layout import add_etch_for_component, merge_component_layers
from orcapen_sc_pdk.helpers.layout.geometry import polar_point, rotate_point
from orcapen_sc_pdk.pdk import PDK
from orcapen_sc_pdk.tech import LAYER

PDK.activate()
assert polar_point(10, 90) == pytest.approx((0, 10))  # radius, angle in degrees
assert rotate_point((10, 0), 90) == pytest.approx((0, 10))  # about the origin
assert gf.kcl.to_dbu(1.5) == 1500  # 1 DBU is 1 nm
assert circle_segments(50, FABRICATION) > 0  # points per circle for this radius and sampling
```

## H2. 新的 helper 函式列在 Issue 上，由 Human 一次核准 {#h2}

**規則。** 把每個不是 `@gf.cell` 的新函式在 Issue 上列出一次，等 Human（儲存庫擁有者）核准這份清單之後再撰寫。

清單對每個函式說明它做什麼，以及為何沒有既有函式適用（H1）。Human 一次核准整份清單。

| 需要 Human 核准 | 不需要核准 |
|---|---|
| 只屬於某個 cell 檔案的新私有函式 | 只包一個運算式、僅在檔案內使用的小型包裝函式 |
| 放在 `orcapen_sc_pdk/helpers/` 下共用的新函式 | 測試用的 helper |

既有的私有函式，會在其 cell 下次改寫時一併審查。

## H3. 部件本身就是一個元件時，才成為 cell {#h3}

**規則。** 部件本身就是一個元件時，把它寫成 `@gf.cell`；當它的形狀或位置來自宿主元件時，把它寫成套用在宿主上的 helper 函式。

部件本身就是一個元件，是指：

- 它的形狀來自它自己的參數，而不是來自它所附著的元件；
- 它有 port，也就是有寬度與方向、供其他部件連接的具名連接點；
- 它可以作為該元件單獨製作與模擬，例如彎管、launcher、交指電容或共振器。

因此彎管這類佈線部件是 cell：它們可以單獨存在，也帶有 port。部件來自宿主，是指它在宿主的某個 port 上或沿著宿主的輪廓修改宿主，例如 CPW port 上的開路端，或畫在導體周圍的蝕刻。這樣的部件是接收宿主的 helper 函式，就像 `add_etch_for_component`。

![**cell。** PDK 的 `bend_euler`：它的形狀來自自己的半徑與 cross-section，兩個 port（箭頭）是其他部件連接的地方。](../_static/images/contributing/zh-TW/h3-cell.svg)

![**套用在宿主上的 helper。** 一段 40 µm 的 CPW 直線段，在它的 port `o2`（箭頭）加上開路端：接地淨空區延伸到 port 外 6 µm，寬度等於宿主 port 的寬度加上兩側間隙。](../_static/images/contributing/zh-TW/h3-helper.svg)

```python
bend = PDK.get_component("bend_euler")  # a cell: its own parameters, its own ports
host = PDK.get_component("straight", length=40)


def add_open_end(host, port_name, gap=6.0):
    """Clear the ground `gap` µm past one of the host's ports; the cap's size comes from that port."""
    c = host.copy()
    port = host.ports[port_name]
    cap = gf.components.rectangle(
        size=(gap, port.dwidth + 2 * gap),
        layer=LAYER.D0_TOP_GROUND_MASK,
        centered=True,
        port_type="optical",
        port_orientations=(0, 180),
    )
    (c << cap).connect("o1", port, allow_width_mismatch=True, allow_layer_mismatch=True)
    return add_etch_for_component(c)  # ETCH = GROUND_MASK − DRAW, as R13 asks


assert [port.name for port in bend.ports] == ["o1", "o2"]
open_ended = add_open_end(host, "o2")
assert open_ended.dbbox().right == pytest.approx(46)  # the 40 µm host plus the 6 µm cap
```

除非 PDK 為某個 GDSFactory 元件加上了幾何或意義，否則不要把它包成 PDK 的 cell（H1）。

## H4. cell 本體依物理部件的順序撰寫 {#h4}

**規則。** cell 本體依物理部件的順序撰寫，每個部件以一行簡短的註解標題開頭；cell 檔案長一點沒有問題。

讀者依部件理解 cell，所以程式碼的順序就是部件在版圖中的順序。成為 cell 的部件（H3），在其他 cell 也用到它時移到自己的模組，讓一次修正能涵蓋所有共用它的 cell。這樣的本體長這樣：

```python
@gf.cell
def pad_with_lead(pad_size: float = 20.0, lead_length: float = 30.0) -> gf.Component:
    c = gf.Component()

    # Pad
    c << gf.components.rectangle(size=(pad_size, pad_size), layer=LAYER.D0_TOP_M1_DRAW)

    # Lead, from the pad's right edge
    lead = c << gf.components.rectangle(size=(lead_length, 4), layer=LAYER.D0_TOP_M1_DRAW)
    lead.dmove((pad_size, pad_size / 2 - 2))

    # Port at the lead's end
    c.add_port("o1", center=(pad_size + lead_length, pad_size / 2), width=4, orientation=0,
               layer=LAYER.D0_TOP_M1_DRAW)
    return c


assert pad_with_lead().ports["o1"].dcenter[0] == pytest.approx(50)
```
