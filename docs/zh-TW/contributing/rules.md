---
title: "規則總覽"
sidebar: development
---

cell 正確，是指它的多邊形就是你想畫的形狀。以下建構規則說明如何建構出這樣的幾何，以及如何檢查。每條規則都來自本 PDK 的 cell 中實測到的失敗，審查者會依這些規則檢查 cell。什麼會成為 cell、要用什麼來建構它，請先閱讀[什麼是 cell](what-is-a-cell.md)。

每個規則頁面都採用相同的形式：一句話的規則、問題的圖、結果的圖、可以單獨執行的範例，以及如何檢查。縮圖顯示每條規則的問題。

## 名詞

- **DBU**（資料庫單位，database unit）：GDS 儲存座標所用的整數格點。本 PDK 的 1 DBU 是 1 nm，所以每個頂點都會捨入到 1 nm 格點。
- **局部座標系**：你繪製形狀所在的 cell 的座標系，在任何旋轉、鏡射或移動把它放進父 cell 之前。
- **合併**：像光罩寫入器一樣，把一個圖層中重疊與相接的多邊形併成最少的多邊形：`component.get_region(layer, merge=True)`。
- **孔洞**：合併後多邊形中被包圍的空隙。GDS 無法儲存孔洞，所以寫入器會以一條切割線把每個孔洞接到外輪廓。
- **弓高**（sagitta）：取樣曲線的弦與它所代表的圓弧之間的最大距離。
- **導體**：一塊應該電性連續的金屬，例如一塊焊墊連同它的導線。
- **XOR**：兩個形狀不同的區域。

## 規則

| 問題 | 規則 | 一句話 |
|---|---|---|
| ![R9 問題](../_static/images/contributing/r9-problem.svg){width=150} | [R9](grid-and-polygons.md#r9) | 每個長度與位置都放在 1 nm 格點上。 |
| ![R10 問題](../_static/images/contributing/r10-problem.svg){width=150} | [R10](grid-and-polygons.md#r10) | 每個多邊形都畫成有效的：不自我相交，也不自我接觸。 |
| ![R11 問題](../_static/images/contributing/r11-problem.svg){width=150} | [R11](grid-and-polygons.md#r11) | 每個導體都自成一個連通的多邊形。 |
| ![R1 問題](../_static/images/contributing/r1-problem.svg){width=150} | [R1](one-outline.md#r1) | 剛體形狀的各部件先在局部座標系合併，再一次旋轉與移動。 |
| ![R6 問題](../_static/images/contributing/r6-problem.svg){width=150} | [R6](one-outline.md#r6) | 先聯集各部件，只做一次圓角，並以延伸再裁切保留方形端。 |
| ![R12 問題](../_static/images/contributing/r12-problem.svg){width=150} | [R12](one-outline.md#r12) | 以布林運算組合形狀，不要串接它們的點列。 |
| ![R2 問題](../_static/images/contributing/r2-problem.svg){width=150} | [R2](placement.md#r2) | 原地轉動部件時繞它的中心；放到圓上時要刻意為之。 |
| | [R3](placement.md#r3) | 轉換 reference，絕不轉換共用的 cell（說明：GDSFactory 已強制執行）。 |
| ![R4 問題](../_static/images/contributing/r4-problem.svg){width=150} | [R4](placement.md#r4) | 鏡射與旋轉不可交換：把鏡射的部件連接到它的 port。 |
| ![R13 問題](../_static/images/contributing/r13-problem.svg){width=150} | [R13](placement.md#r13) | 以 `connect` 在 port 處接合部件，並在局部座標系中進行。 |
| ![R5 問題](../_static/images/contributing/r5-problem.svg){width=150} | [R5](curves.md#r5) | 直邊與曲線相接處，讓直邊延伸進本體。 |
| ![R14 問題](../_static/images/contributing/r14-problem.svg){width=150} | [R14](curves.md#r14) | 直邊或切割線跨過取樣曲線時，讓兩者共用一個頂點。 |
| ![R15 問題](../_static/images/contributing/r15-problem.svg){width=150} | [R15](companion-layers.md#r15) | 光罩以金屬的來源繪製，蝕刻由兩者推導。 |
| ![R7b 問題](../_static/images/contributing/r7b-problem.svg){width=150} | [R7](input-checks.md) | 先修正建構方式；拒絕畫不出的值與不在格點上的輸入；絕不掩蓋症狀。 |
| ![R8 問題](../_static/images/contributing/r8-problem.svg){width=150} | [R8](construction-checks.md) | 對 cell 支援的每一種建構執行建構檢查。 |

R1 到 R8 保留原本的編號，R9 到 R15 是後來加入的，所以表格依閱讀順序而不是依編號排列。

建構檢查是三種檢查之一，各有自己的負責方；請見[三種檢查與製程規則](checks-and-process-rules.md)。
