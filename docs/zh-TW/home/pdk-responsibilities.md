---
title: "PDK 與模擬職責"
sidebar: development
---

OrcaPen 定義可重複使用的公開製程輸入與來源佈局。SCGSim 解讀這些輸入以進行模擬；使用套件的設計專案提供裝置專屬幾何與選擇。

| OrcaPen | SCGSim | 使用套件的設計專案 |
| --- | --- | --- |
| 材料、圖層、實體堆疊、橫截面、可重複使用元件、來源標註 | 幾何解讀、後端指派、網格生成、求解器交接與結果 | 裝置尺寸、組裝、最終網路、參考導體與激發條件 |

PDK 輸入請見[圖層與堆疊](../start/layers.qmd)及[材料與介面](../start/materials.qmd)；教學請見[模擬](../notebooks.qmd)；套件關係請見[工作區與相關套件](ecosystem-workspace.md)。

請將私有裝置幾何、參數、佈局與模擬紀錄保存在使用套件的設計儲存庫。[QPDK](https://github.com/gdsfactory/quantum-rf-pdk)是外部參考與範例來源，不是 OrcaPen 語意或 SCGSim 執行環境的依據。
