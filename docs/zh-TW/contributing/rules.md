---
title: "規則總覽"
sidebar: development
page-navigation: true
---

cell 正確，是指它的多邊形就是你想畫的形狀。以下建構規則說明如何建構出這樣的幾何，以及如何檢查。每條規則都來自本 PDK 的 cell 中實測到的失敗，審查者會依這些規則檢查 cell。什麼會成為 cell、要用什麼來建構它，請先閱讀[什麼是 cell](what-is-a-cell.md)。

每個規則頁面都採用相同的形式：一句話的規則、問題的圖、結果的圖、可以單獨執行的範例，以及如何檢查。縮圖顯示每條規則的問題。

## 如何閱讀圖

- 每個合併後的多邊形各有一種顏色（依序為青綠、琥珀、紫、藍、粉紅），所以散開的導體會呈現兩種顏色。
- 紅色標出缺陷：缺陷周圍的圓圈，或兩個形狀不同處的紅色區域。
- 虛線輪廓是用來比較的形狀：預期的形狀，或部件的起始位置。
- 箭頭是 port，指向它面對的方向。
- 右側若有面板，它會放大缺陷；結果圖放大的是同一個位置。
- 圖層的顏色是青綠色 `DRAW`、灰色 `GROUND_MASK`、琥珀色 `ETCH`。圖層圖要不是每個圖層一個面板，就是多個圖層共用一個面板並附上圖例；這時顏色代表圖層，而不是不同的多邊形。

## 名詞

- **DBU**（資料庫單位，database unit）：GDS 儲存座標所用的整數格點。本 PDK 的 1 DBU 是 1 nm，所以每個頂點都會捨入到 1 nm 格點。
- **局部座標系**：你繪製形狀所在的 cell 的座標系，在任何旋轉、鏡射或移動把它放進父 cell 之前。
- **合併**：像光罩寫入器一樣，把一個圖層中重疊與相接的多邊形併成最少的多邊形：`component.get_region(layer, merge=True)`。
- **孔洞**：合併後多邊形中被包圍的空隙。GDS 無法儲存孔洞，所以寫入器會以一條切割線把每個孔洞接到外輪廓。
- **弓高**（sagitta）：取樣曲線的弦與它所代表的圓弧之間的最大距離。
- **導體**：一塊應該電性連續的金屬，例如一塊焊墊連同它的導線。
- **XOR**：兩個形狀不重疊的部分，也就是兩者不同的地方。

## 規則

| 問題 | 規則 | 一句話 |
|---|---|---|
| ![R1 問題](../_static/images/contributing/zh-TW/r1-problem.svg){width=150} | [R1](grid-and-polygons.md#r1) | 每個長度與位置都放在 1 nm 格點上。 |
| ![R2 問題](../_static/images/contributing/zh-TW/r2-problem.svg){width=150} | [R2](grid-and-polygons.md#r2) | 每個多邊形都畫成有效的：不自我相交，也不自我接觸。 |
| ![R3 問題](../_static/images/contributing/zh-TW/r3-problem.svg){width=150} | [R3](grid-and-polygons.md#r3) | 每個導體都自成一個連通的多邊形。 |
| ![R4 問題](../_static/images/contributing/zh-TW/r4-problem.svg){width=150} | [R4](one-outline.md#r4) | 剛體形狀的各部件先在局部座標系合併，再一次旋轉與移動。 |
| ![R5 問題](../_static/images/contributing/zh-TW/r5-problem.svg){width=150} | [R5](one-outline.md#r5) | 導體在所有部件接合之後，只做一次圓角。 |
| ![R6 問題](../_static/images/contributing/zh-TW/r6-problem.svg){width=150} | [R6](one-outline.md#r6) | 以布林運算組合形狀，不要串接它們的點列。 |
| ![R7 問題](../_static/images/contributing/zh-TW/r7-problem.svg){width=150} | [R7](placement.md#r7) | 繞部件自己的中心轉動；放到圓上時，先在原點轉動再移出去。 |
| | [R8](placement.md#r8) | 轉換 reference，絕不轉換共用的 cell（說明：GDSFactory 已強制執行）。 |
| ![R9 問題](../_static/images/contributing/zh-TW/r9-problem.svg){width=150} | [R9](placement.md#r9) | 以 `connect(..., mirror=True)` 擺放鏡射的部件。 |
| ![R10 問題](../_static/images/contributing/zh-TW/r10-problem.svg){width=150} | [R10](placement.md#r10) | 在 0°、90°、180° 或 270° 以 `connect` 接合部件，再旋轉合併後的結果。 |
| ![R11 問題](../_static/images/contributing/zh-TW/r11-problem.svg){width=150} | [R11](curves.md#r11) | 直邊與曲線相接處，讓直邊延伸進本體。 |
| ![R12 問題](../_static/images/contributing/zh-TW/r12-problem.svg){width=150} | [R12](curves.md#r12) | 直邊或切割線跨過取樣曲線時，讓兩者共用一個頂點。 |
| ![R13 問題](../_static/images/contributing/zh-TW/r13-problem.svg){width=150} | [R13](companion-layers.md#r13) | 由與金屬一起繪製的光罩推導蝕刻。 |
| ![R14 問題](../_static/images/contributing/zh-TW/r11-problem.svg){width=150} | [R14](input-checks.md#r14) | 先修正建構方式，再限制輸入。 |
| ![R15 問題](../_static/images/contributing/zh-TW/r15-problem.svg){width=150} | [R15](input-checks.md#r15) | 拒絕建構方式畫不出的值，絕不夾限。 |
| ![R16 問題](../_static/images/contributing/zh-TW/r1-problem.svg){width=150} | [R16](input-checks.md#r16) | 拒絕不在格點上的輸入。 |
| ![R17 問題](../_static/images/contributing/zh-TW/r17-problem.svg){width=150} | [R17](input-checks.md#r17) | 修正缺陷的原因，而不是把它補起來。 |
| ![R18 問題](../_static/images/contributing/zh-TW/r18-problem.svg){width=150} | [R18](construction-checks.md#r18) | 對 cell 支援的每一種建構執行 `construction_report`。 |

建構檢查是三種檢查之一，各有自己的負責方；請見[三種檢查與製程規則](checks-and-process-rules.md)。
