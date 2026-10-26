---
title: "模型圖集（Model Gallery）"
sidebar: simulation
---

這七類公開來源版圖可用於檢視墊片、曲線金屬帶、有限寬接地共面波導（coplanar waveguide，CPW）與多層結構。縮圖顯示實際來源多邊形，點選 **Image** 可開啟完整視圖與細節面板。座標單位為微米；顏色區分正形金屬、基板輪廓、遮罩與非金屬定位標記，不是求解器結果。

| 類別與原始碼 | 依原始碼產生的版圖 |
| --- | --- |
| **01 方形墊片（Square pad）** — [`square_pad_capacitor()`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/simulation/scgsim/simple_pad.py). 預設為 200 µm 孤島與 20 µm 開口間隙，並帶有非金屬接面定位標記。 | ![方形墊片的輪廓與開口細節。](../_static/images/test-components/01-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/01-source.png" label="檢視：01 方形墊片" >}} |
| **02 圓盤（Circular disk）** — [`circular_pad_capacitor()`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/simulation/scgsim/simple_pad.py). 外半徑為 100 µm，內半徑為零。 | ![圓盤的輪廓與定位標記細節。](../_static/images/test-components/02-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/02-source.png" label="檢視：02 圓盤" >}} |
| **03 圓環（Annulus）** — 同一圓形工廠函式設定 `inner_radius_um=80`。內孔為非金屬，不是接地（Ground）。 | ![圓環的實際內孔與外側開口。](../_static/images/test-components/03-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/03-source.png" label="檢視：03 圓環" >}} |
| **04A 圓弧金屬帶（Circular-arc strip）** — [`straight_to_circular_strip()`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/simulation/scgsim/simple_pad.py). 直線部分接至來源圓弧；沒有背景接地或約瑟夫森接面（Josephson junction，JJ）。 | ![圓弧金屬帶的輪廓與端點細節。](../_static/images/test-components/04a-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/04a-source.png" label="檢視：04A 圓弧金屬帶" >}} |
| **04B 插值金屬帶（Interpolation strip）** — [`interpolation_spline_strip()`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/simulation/scgsim/spline_strip.py). 通過來源點的分段三次 Hermite 曲線。 | ![插值金屬帶的實際來源多邊形與連接埠。](../_static/images/test-components/04b-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/04b-source.png" label="檢視：04B 插值金屬帶" >}} |
| **04C B 樣條（B-spline）金屬帶** — [`bspline_strip()`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/simulation/scgsim/spline_strip.py). 明確指定控制點、節點與權重的三次有理 B-spline。 | ![B-spline 金屬帶的實際來源多邊形與連接埠。](../_static/images/test-components/04c-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/04c-source.png" label="檢視：04C B-spline 金屬帶" >}} |
| **05 有限寬接地 CPW** — `finite_ground_cpw_coupon()`. PDK 基板上的三個導體矩形：長度 500 µm、訊號寬度 10 µm、間隙 6 µm、接地寬度 80 µm。 | ![有限寬接地 CPW 的來源矩形與基板。](../_static/images/test-components/05-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/05-source.png" label="檢視：05 有限寬接地 CPW" >}} |
| **06 覆晶墊片（Flip-chip pad）** — [`flip_chip_pad_coupon()`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/simulation/scgsim/test_components.py). 下方墊片、上方晶片底面的完整平面，以及位於 (±250, ±250) µm 的四個既有凸塊。 | ![覆晶來源幾何的上下表面分離視圖與凸塊細節。](../_static/images/test-components/06-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/06-source.png" label="檢視：06 覆晶墊片" >}} |
| **07 CPW 空氣橋（Airbridge）** — [`cpw_airbridge_coupon()`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/simulation/scgsim/test_components.py). 正形 CPW 搭配既有橋面與兩個支柱，從訊號（Signal）上方跨越。 | ![空氣橋來源幾何的 CPW 跨越與實際支柱重疊細節。](../_static/images/test-components/07-source.png){width=220} {{< askr-image-view src="../_static/images/test-components/07-source.png" label="檢視：07 CPW 空氣橋" >}} |

## 端點驅動（Driven Terminal）：集總埠（Lumped Port）與波埠（Wave Port）比較 {#driven-terminal-lumped-and-wave-port-comparison}

這組來源版圖使用相同的貫通 CPW、多導體傳輸線（multiconductor transmission line，MTL）直線耦合段，以及一端短路、一端開路的蛇形共振器。讀者可在固定共振器、接地與空氣橋的條件下，比較激發幾何形狀。這些圖用於檢視來源幾何形狀，不是原生連接埠指定或求解器結果。

| 版圖 | 依來源產生的檢視圖 |
| --- | --- |
| **集總埠**——兩個饋入元件，以及內部非金屬 Signal–Ground 片。 | ![集總埠來源版圖的共用共振器、空氣橋放置與內部片細節。](../_static/images/test-components/driven-terminal-lumped-resonator.png){width=260} {{< askr-image-view src="../_static/images/test-components/driven-terminal-lumped-resonator.png" label="檢視：集總埠比較" >}} |
| **波埠**——沒有饋入元件；等寬 CPW 終止於有限邊界。 | ![波埠來源版圖的相同共振器與空氣橋，以及在邊界截切的 CPW 端點。](../_static/images/test-components/driven-terminal-wave-resonator.png){width=260} {{< askr-image-view src="../_static/images/test-components/driven-terminal-wave-resonator.png" label="檢視：波埠比較" >}} |

| 激發細節 | 集總埠 | 波埠 |
| --- | --- | --- |
| 端部幾何形狀 | 饋入墊片與漸變段 | 邊界截切 CPW；無饋入元件或漸變段 |
| 片的用途 | 每個饋入元件端部間隙內既有的 85 × 150 µm 非金屬片 | 各 CPW 截切處所提議的外部 YZ 片 |
| 提議方向 | 片法向量 +Z；積分方向 Signal → Ground | 外法向量 −X／+X；Signal 兩側接地作為參考 |
| 目前狀態 | 來源片幾何形狀，尚非已指定的原生端點 | 邊界幾何形狀與提議的波埠片用途，尚非已求解的連接埠模態 |

每個版圖都有 **17 個空氣橋**：11 個位於等寬貫通引線，6 個位於標準蛇形直線段的中心。最低一排蛇形段省略空氣橋，因為相同橋跨距也會跨過貫通傳輸線。貫通段空氣橋避開耦合區與相鄰轉折排除區；饋入元件、漸變段、彎曲與開路圓頭上都沒有空氣橋。放置位置與節距是預覽設定，不是製程規則，也不代表已證實能抑制槽線模態。

這些組件採用寬 12 µm 的中央橋面，兩端具有 **14 × 14 µm 完整落腳區**，覆蓋既有的 14 × 14 µm 支柱。橋面總跨距為 98 µm。此組件專用形狀與上方未變更的第 07 類不同；第 07 類的標準橋面僅部分覆蓋各支柱。共用來源堆疊為 100 nm 基底 M1、M1 上方 3 µm 高支柱及 0.3 µm 橋面：支柱 Z = 0.1–3.1 µm，橋面 Z = 3.1–3.4 µm。實體圖層與堆疊請見[圖層與堆疊](../start/layers.qmd)。

選定的[公開 PDK 原始碼（英文）](https://github.com/OrPenStrike/orcapen-sc-pdk/tree/7f89c3381097ac894705e8c54434ebfbfc758693)提供 `cpw_meander_airbridge_lumped_coupon()` 與 `cpw_meander_airbridge_wave_coupon()`。兩者共用同一來源實作，並提供完整的本體、實例與中性支撐宣告。[Notebook 目錄](../simulation/notebooks.qmd)連結具體的 RLC 與端點建模範例，選擇原生計算時請依各教學標示的狀態操作。一端短路、一端開路的拓撲不代表已確立目標頻率、精確四分之一波長設計、原生連通性，或集總埠／波埠等價性。

## 建立已註冊的來源版圖 {#build-a-registered-source-layout}

先閱讀[安裝與啟用](../getting-started.md)，再從[元件](index.md)選擇工廠函式。實體高度請見[圖層與堆疊](../start/layers.qmd)，模型性質請見[材料與介面](../start/materials.qmd)。

## 閱讀曲線金屬帶變體 {#reading-the-curved-strip-variants}

04B 通過 (−200, 0)、(−100, 60)、(0, −40)、(100, 60)、(200, 0) µm 進行插值。端點斜率為零，內部斜率使用中心割線。來源多邊形在每段 Hermite 曲線上採用 32 個均勻參數位置，另加最終端點。SCG 原生 OCC 插值採用不同曲線法則，因此通過相同點不表示原生曲線精確等價。

04C 使用控制點 (−200, 0)、(−100, 0)、(0, 150)、(100, −30)、(200, −30) µm，次數為 3，權重皆為 1，不重複節點為 (0, 0.5, 1)，重數為 (4, 1, 4)。控制點不是曲線必須通過的點。來源多邊形在每個節點區間採用 64 個均勻參數取樣，另加最終端點；不進行擬合。

兩種樣條金屬帶的邊界曲線在 Y 方向相距 10 µm，不是固定法向寬度。端部封口閉合實際金屬多邊形，`o1` 與 `o2` 沿端點切線方向。完整的 110/0 遮罩未宣告背景接地。這些金屬帶工廠函式不指定最終電氣網路（Net）、接地或 JJ。

## 閱讀多層視圖 {#reading-the-multi-level-views}

06 將上層表面分開顯示，避免其完整平面遮住四個凸塊。上層金屬是上方晶片的**底面**，向外方向為 −Z，位於 Z = 8.1–8.2 µm。銦凸塊跨越 0.1–8.1 µm；40/1 凸塊下金屬化層（under-bump metallization，UBM）輪廓仍是獨立的來源製程細節，依 PDK 規則不納入模擬。此組件不轉交下層子元件未使用的非金屬定位標記。

07 依圖層分開顯示 Signal、兩側接地、橋面 10/0 與支柱 10/1。支柱跨越 Z = 0.1–3.1 µm，橋面跨越 3.1–3.4 µm。實際橋面尺寸為 12 × 84 µm，14 × 14 µm 支柱位於 Y = ±42 µm；每處橋面／支柱重疊面積為 12 × 7 µm，並未完整覆蓋支柱。來源接觸用途不代表已驗證原生連通性。

## 模擬適用範圍 {#simulation-scope}

[Notebook 目錄](../simulation/notebooks.qmd)將需求連結至指定版本的墊片／CPW 建模，以及 04A/B/C、06 與 07 的來源幾何觀察。目前乾淨的 Notebook 未附執行輸出；這些來源圖片不表示已完成原生轉換、接觸一致性、網格品質或求解器成功檢查。

05 保留既有矩形與基板。目前 3D 範例使用 PDK 鋁堆疊，歷史 Nb／薄片輸出維持原本模型。Q2D CPW 範例採用 10 µm 間隙與 40 µm 接地寬度，不同於此 3D 試片的 6 µm 間隙與 80 µm 接地寬度，不能自動視為等價切片。歷史 200 nm M1 紀錄仍保留原始身分，不改標為目前的 100 nm 預設值。
