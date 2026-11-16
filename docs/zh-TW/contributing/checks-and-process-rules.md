---
title: "三種檢查與製程規則"
sidebar: development
---

適用於版圖的檢查有三種。它們回答不同的問題、有不同的負責方，也觸及不同的使用者，所以其中一種通過，不代表其他種也通過。

| 種類 | 問題 | 負責方 | 目前在哪裡執行 |
|---|---|---|---|
| [建構檢查](construction-checks.md) | 程式碼畫出的是不是它想畫的？有效的多邊形、沒有短於 2 DBU（2 nm）的邊、只有刻意的孔洞、每個導體一個多邊形、符合預期形狀；最小內角只回報 | 本 PDK，在其測試中 | `disk_flip_chip_qubit` 的 `tests/test_disk_qubit.py`。其他 cell 隨著測試撰寫而補上。使用端可以對自己的佈局呼叫 `construction_report` |
| 製程設計規則（DRC） | 製程做得出來嗎？每個圖層的寬度、間距與包覆 | 本 PDK | 尚無：目前沒有任何已採用的製程規則。規則建立之後，使用端可以採用、修改或忽略 |
| 模擬檢查 | 求解器能建模嗎？ | [SCGSim](https://github.com/NCUPHY-LTLab/scgsim) | 由 SCGSim 定義與執行。它的 [Supported Geometry](https://github.com/NCUPHY-LTLab/scgsim/blob/develop/docs/supported-geometry.qmd) 頁面列出它接受的幾何，[Known Geometry Problems](https://github.com/NCUPHY-LTLab/scgsim/blob/develop/docs/known-geometry-problems.qmd) 則列出它不會代為處理的繪圖缺陷 |

PDK 的使用端不必遵循它的製程規則。

## 記錄製程規則

製程規則陳述製造製程的限制，例如某個圖層的最小寬度。製程規則不自行發明：每一條都附有 PDK 維護者提供的來源。

要提出一條規則，請在本儲存庫開一個 Issue，並記錄：

- **來源**：數值出自何處。
- **圖層**：適用的圖層或圖層組合。
- **數值**：數字與單位。
- **狀態**：在 PDK 維護者採用之前為 `proposed`，採用之後為 `adopted`。

規則是否採用由 PDK 維護者決定。第一條被採用的規則，會在本指南加入一個列出製程規則的頁面，以及檢查這些規則的程式碼。

建構檢查的 2 DBU 下限不是製程規則：不論製程為何，它都是繪圖所能表達的最短邊。
