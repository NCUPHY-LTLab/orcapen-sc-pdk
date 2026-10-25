---
title: "搭配 OrcaPen 使用 GDSFactory"
sidebar: get-started
---

使用 GDSFactory 指南學習元件（Component）組裝，再用 OrcaPen 指南選擇製程與元件。先依[安裝與啟用](../getting-started.md)註冊 OrcaPen 的元件與橫截面（cross-section）。

| 工作 | 閱讀內容 |
| --- | --- |
| 建立元件、放置幾何形狀及匯出 GDS | [GDSFactory 元件基礎（英文）](https://gdsfactory.github.io/gdsfactory/notebooks/00_geometry/) |
| 放置實例（Instance）並連接其實際連接埠（Port） | [GDSFactory 實例與連接埠（英文）](https://gdsfactory.github.io/gdsfactory/notebooks/01_references/) |
| 在連接埠之間佈線 | [GDSFactory 佈線（英文）](https://gdsfactory.github.io/gdsfactory/notebooks/04_routing/) |
| 選擇 OrcaPen 工廠函式與基本元件 | [元件](index.md)與[共用基本元件](shared-primitives.md) |
| 選擇製程圖層、實體高度與材料 | [圖層與堆疊](../start/layers.qmd)及[材料與介面](../start/materials.qmd) |
| 選擇橫截面或理解定位標記 | [橫截面](cross-sections.qmd)與[模擬連接埠](../simulation/requirements/driven-terminal.qmd#geometric-ports-simulation-locators-and-terminals) |

使用具名 PDK 工廠函式或橫截面時，請保持 OrcaPen 啟用，並使用與已安裝套件版本相符的 GDSFactory API。
