---
title: "工作區與相關套件"
sidebar: development
---

使用 OrcaPen 查閱 PDK 資訊與來源佈局，使用 GDSFactory 組合佈局，並以 SCGSim 進行模擬。各套件的版本應與使用它的專案一併記錄。

| 套件或專案 | 提供內容 |
| --- | --- |
| [OrcaPen](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk) | 公開元件、橫截面、圖層、堆疊、材料與元件模擬範例 |
| [GDSFactory](https://gdsfactory.github.io/gdsfactory/) | 元件建構、放置、連接、佈線與 GDS 匯出 |
| [SCGSim](https://github.com/OrPenStrike/scgsim) | 幾何詮釋、Palace／AEDT 準備、交接與回傳結果分析 |
| 你的佈局專案 | 元件參數、晶片組裝、最終 Nets 與激發，以及私人結果 |

## 依任務選擇執行環境

核心安裝支援佈局使用。模擬教學可能需要不同於儲存庫一般相依套件群組的 SCGSim 修訂版或求解器安裝；請依該教學指定的設定操作。

[安裝與啟用](../getting-started.md)說明公開原始碼安裝；[選擇模擬](../notebooks.qmd)提供電氣計算入口；[SCGSim 整合](../features/scgsim-integration.md)說明哪些紀錄會在套件間傳遞。

## 僅分享公開輸入

提交至 OrcaPen 的範例應使用公開佈局與參數。私人設計與其輸出應保留在私人專案中，讓公開文件建置不需要私人檔案。
