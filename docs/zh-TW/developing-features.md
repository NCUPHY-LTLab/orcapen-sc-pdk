---
title: "參與貢獻"
sidebar: development
---

透過[公開儲存庫](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk)貢獻可重複利用的元件、製程紀錄、範例或文件。請從變更所影響的 PDK 部分著手。

## 建立開發工作目錄

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12 --extra dev
```

確認：`uv run python --version` 會回報支援的 Python 版本。文件相依套件與預覽方式請見[文件與網站](docs-publishing.md)。

## 讓變更聚焦

- 在 OrcaPen 放置可重複利用的佈局與製程定義。
- 使用 GDSFactory 組合元件與佈線。
- 使用 SCGSim 準備模擬、整合求解器並分析回傳結果。
- 將私人佈局、參數與執行目錄保留在使用端專案。

新增介面前，先檢查相關既有原始碼與範例。將相關文件放在描述其公開行為的位置。

## 提交變更

在提取要求中說明變更的行為、受影響的公開介面及已執行的檢查。已儲存的科學結果應與原始模型及執行環境對應；修改教學不會重新執行結果。

套件角色請見[工作區與相關套件](home/ecosystem-workspace.md)；來源與執行期的界線請見[SCGSim 整合](features/scgsim-integration.md)；筆記本配對與部署請見[文件與網站](docs-publishing.md)。
