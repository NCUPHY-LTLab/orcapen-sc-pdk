---
title: "共用版圖基本元件（Shared layout primitives）"
sidebar: get-started
---

這四個已註冊工廠函式（factory）提供公開來源的幾何形狀，不是電氣模型、原生模擬輸入或製程目標。示意預覽採用公開的 7/10 µm 導線、6 µm 間距與 100 µm 佈線半徑。啟用 OrcaPen 後，可從 `orcapen_sc_pdk.cells` 匯入，或用 `gf.get_component` 依註冊名稱建立。

## 共面波導銜接段（CPW handoff） {#cpw-handoff}

`cpw_handoff(length=200, taper_length=50, native_width=10, native_gap=6,
route_width=7, route_gap=6, radius=100, draw_layer=..., etch_layer=...,
ground_mask_layer=...)` 重用公開的共面波導（coplanar waveguide，CPW）橫截面、直線段與漸變段。直線段佔 `length - taper_length`，出口漸變段只在總長度中計入一次。`o1` 位於 `(0, 0)`、朝向 180°，採原始寬度；`o2` 位於 `(length, 0)`、朝向 0°，採佈線寬度。兩個連接埠都在 DRAW 上。半徑是橫截面／佈線中繼資料，不表示此直線元件內有彎曲。

長度須為正值，且 `0 <= taper_length <= length`，也支援僅有漸變段的情況。漸變段長度為零時，原始端與佈線端的寬度**及間隙**都須相同；工廠函式不會藉由更改連接埠寬度來掩蓋缺少的過渡段。無效導線／間隙輸入由既有橫截面與原生 GF 錯誤處理。

## 單端圓頭金屬線段 {#metal-segment-with-one-rounded-end}

`rounded_end_metal_segment(length=100, width=10, ground_mask_margin=6,
n_cap_points=17, draw_layer=..., etch_layer=..., ground_mask_layer=...)`
在局部 X=0 有平面端，右端為半圓。圓頭半徑為 `width/2`，中心位於 `(length-width/2, 0)`，頂端位於 `(length, 0)`。長度只包含一次圓頭範圍，不代表共振器長度或電氣長度。寬度須為正值，且 `length >= width/2`。半圓每四分之一圓弧使用 `n_cap_points` 個取樣點，包含頂點與端點；每四分之一圓弧至少需要兩點，才能保留端點。

單一 DRAW 多邊形透過公開 GF 偏移操作，以 µm 為單位並使用預設轉角模式，向外擴張產生 GroundMask。ETCH 為 `MASK - DRAW`。這是多邊形偏移幾何形狀，不表示精確的解析偏移圓。非負邊距是來源間距輸入，不是網格尺寸規則。

佈線連接埠 `o1` 位於 `(0, 0)`，朝向 180°，寬度為導線寬度。`o_mesh` 是 DRAW 上位於圓頭中心的具名網格區域定位標記（mesh-region locator），朝向 0°，寬度為導線寬度；它**不是**第二個佈線連接埠、接面、負載或已指定的求解器網格。

在 `length == width/2` 時，形狀為半圓盤：`o_mesh` 位於平面邊界上，與 `o1` 中心相同、朝向相反，且定位標記類型不同。圓頭中心標記不保證嚴格位於內部。私有的多項長度與放置偏移仍由呼叫端組裝：呼叫端提供計算後的幾何長度，並放置平面端錨點。

## 圓角矩形（Rounded rectangle） {#rounded-rectangle}

`rounded_rectangle(width=100, height=50, corner_radius=7,
n_corner_points=20, ground_mask_margin=6, draw_layer=...,
ground_mask_layer=None, port_type="electrical")` 將置中的 DRAW 多邊形交給 `gf.components.rounded_rectangle` 建立，X／Y 圓角半徑相同。尺寸須為正值，且 `0 <= corner_radius <= min(width,height)/2`；超出可容納範圍的半徑會被拒絕，不會自動縮小。取樣數是 GF **每個圓角**的點數，不是私有 KLayout 整體圓角化參數。`n_corner_points` 須包含四分之一圓弧的兩個端點。

選用 GroundMask 是獨立的圓角矩形，尺寸為 `width+2*margin`、`height+2*margin`，半徑為 `corner_radius+margin`。它沒有連接埠，且此工廠函式不產生 ETCH。指定遮罩時邊距須非負；未指定遮罩時不使用邊距。

`port_type=None` 表示不提供連接埠。其他情況會轉交 GF 實際的邊緣連接埠與命名：側邊連接埠寬度為 `height-2*radius`，上／下邊連接埠寬度為 `width-2*radius`，不是矩形原本的完整邊長。退化寬度的命名、接腳與錯誤由 GF 處理。因此，取樣與連接埠都**不同於**私有圓角矩形輔助函式；兩者不宣稱來源等價，呼叫端須明確調整取樣與連接埠假設。

## 導線轉角（Wire corner） {#wire-corner}

`wire_corner(cross_section="cpw_6_7_6", port_names=("e1","e2"),
port_types=("electrical","electrical"), width=None, radius=None)` 是 GF 原廠導線轉角的薄層介面。所選 GF 9.48 接受但忽略半徑，因此這是尖角，而非曲線彎曲。橫截面寬度為 W 時，原生連接埠分別位於 `(-W/2,0)`、朝向 180°，以及 `(0,W/2)`、朝向 90°。橫截面邊界幾何形狀、電氣接腳與連接埠約定由 GF 定義。橫截面仍由呼叫端明確選擇，不複製私有 CPW 預設值。

## 使用基本元件 {#use-the-primitives}

在已啟用的 PDK 中使用公開註冊名稱。組裝版圖時，請保留各工廠函式的取樣方式與連接埠用途；另見[橫截面](cross-sections.qmd)與 [GDSFactory 指南](component-authoring.md)。
