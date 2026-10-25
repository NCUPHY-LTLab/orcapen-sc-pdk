---
title: "元件（Cells）"
sidebar: api
---

依所需幾何形狀選擇已註冊的 OrcaPen 工廠函式（factory）。先啟用製程設計套件（process design kit，PDK），再閱讀[元件指南](components/index.qmd)，確認預設值、連接埠（port）與圖層後再修改尺寸。

使用路徑型元件時，請在[橫截面](cross-sections.qmd)中選擇寬度、間隙與圖層組成，包含共面波導（coplanar waveguide，CPW）、耦合導線及帶狀導線。

| 類別 | 元件指南 |
| --- | --- |
| 共面波導與共振器 | [straight](components/straight.qmd), [taper](components/taper.qmd), [resonator](components/resonator.qmd), [resonator_hanger](components/resonator_hanger.qmd), [resonator_meander](components/resonator_meander.qmd) |
| 電容器 | [interdigital_capacitor](components/interdigital_capacitor.qmd), [martinis2022_differential_ribbon_capacitor](components/martinis2022_differential_ribbon_capacitor.qmd) |
| 連接結構 | [launcher](components/launcher.qmd), [cpw_t_junction](components/cpw_t_junction.qmd), [airbridge](components/airbridge.qmd), [indium_bump](components/indium_bump.qmd), [indium_ground](components/indium_ground.qmd) |
| 基本元件 | [cpw_handoff](components/cpw_handoff.qmd), [rounded_end_metal_segment](components/rounded_end_metal_segment.qmd), [rounded_rectangle](components/rounded_rectangle.qmd), [wire_corner](components/wire_corner.qmd) |
| 模擬版圖 | [模型圖集](test-components.md)中的方形／圓形墊片、有限寬接地 CPW、帶狀導線、覆晶、空氣橋與矽穿孔模型 |

函式簽章請見[自動產生的元件 API（英文）](/orcapen-sc-pdk/en/reference/index.html#cells)，連接用途請見[共用基本元件](shared-primitives.md)，放置、連接與佈線方式請見 [GDSFactory 指南](component-authoring.md)。

## 以平面標籤選擇元件 {#choose-a-cell-with-flat-tags}

工廠函式使用平面中繼資料標籤，描述用途（`layout` 或 `simulation`）、物件（`capacitor`、`resonator`、`cpw`）與特徵（例如 `airbridge` 或 `flip_chip`）。標籤協助尋找原始幾何形狀；若要研究電氣行為，請另選[模擬教學](../notebooks.qmd)。

## 元件版圖 {#components-layout}

預設版圖預覽以深藍綠色顯示 DRAW，淺藍綠色顯示 ETCH。使用 **+ / −**、拖曳、**Fit** 或 **Expand** 檢視圖片。

### 共振器（Resonator） {#resonator}

[工廠函式原始碼（英文）： `resonator`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/layout/resonator.py)
由懸掛段與蛇形段建立 CPW 共振器。

![預設共振器的實際 DRAW 與 ETCH。](../_static/images/components/resonator.svg){#fig-layout-resonator}

{{< askr-image-view target="fig-layout-resonator" mode="inline" >}}

### 指叉電容（Interdigital capacitor） {#interdigital-capacitor}

[元件指南](components/interdigital_capacitor.qmd)說明工廠函式設定與圓角半徑行為。下圖為預設尖角版圖。

![預設指叉電容的實際 DRAW 與 ETCH。](../_static/images/components/interdigital_capacitor.svg){#fig-layout-idc}

{{< askr-image-view target="fig-layout-idc" mode="inline" >}}

### Martinis 帶狀電容 {#martinis-ribbon-capacitor}

[工廠函式原始碼（英文）： `martinis2022_differential_ribbon_capacitor`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/layout/martinis.py)
提供差動帶狀電容版圖。

![預設 Martinis 帶狀電容僅有實際 DRAW；原始碼沒有 ETCH。](../_static/images/components/martinis2022_differential_ribbon_capacitor.svg){#fig-layout-martinis}

{{< askr-image-view target="fig-layout-martinis" mode="inline" >}}

### 饋入元件（Launcher） {#launcher}

[工廠函式原始碼（英文）： `launcher`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/layout/cpw.py)
提供 CPW 饋入元件版圖。

![預設 CPW 饋入元件的實際 DRAW 與 ETCH。](../_static/images/components/launcher.svg){#fig-layout-launcher}

{{< askr-image-view target="fig-layout-launcher" mode="inline" >}}

### 凸塊幾何形狀（Bump geometry） {#bump-geometry}

[工廠函式原始碼（英文）： `indium_ground`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/layout/indium.py)
提供銦凸塊 `40/0` 與凸塊下金屬化層（under-bump metallization，UBM）`40/1` 的輪廓，不含 M1 DRAW／ETCH。分層凸塊幾何形狀請見[測試模型的覆晶視圖](test-components.md#reading-the-multi-level-views)。
