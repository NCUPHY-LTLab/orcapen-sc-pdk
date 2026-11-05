---
title: "參與貢獻"
sidebar: development
---

透過[公開儲存庫](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk)貢獻可重複利用的元件、製程紀錄、範例或文件。請從變更所影響的 PDK 部分著手。

## 建立開發工作目錄

GDSFactory+ 是選用工具，且需要付費訂閱。請擇一設定。

**不使用 GDSFactory+**（以 KLayout 檢視）：

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12
```

這會安裝 PDK 與開發工具 pytest、Ruff。要檢視佈局，請安裝 [KLayout](https://www.klayout.de/) 及其 klive 外掛。

**使用 GDSFactory+**（VS Code 擴充套件）：

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12 --all-extras
```

`--all-extras` 會加入 `gdsfactoryplus` extra，內含 GDSFactory+ Worker Health 所需的套件，包括 SPICE 用的 InSpice 與 vacask。擴充套件的 **Setup Automatically** 執行的也是這個指令。之後請持續使用 `--all-extras`：一般的 `uv sync` 會移除這些套件，擴充套件就會看不到元件。GDSFactory+ 需要 Python 3.12。

確認：`uv run python --version` 會回報支援的 Python 版本。文件相依套件與預覽方式請見[文件與網站](docs-publishing.md)。

## 預覽元件

每個 cell 模組的結尾都有預覽區塊。直接執行該檔案即可，例如在 VS Code 按 **Run Python File**：

```bash
uv run python orcapen_sc_pdk/cells/layout/resonator.py
```

也可以用名稱預覽任何已註冊的 cell：

```bash
uv run python -m orcapen_sc_pdk.preview resonator
```

兩者都會寫出 `build/gds/<cell>.gds` 並開啟。在已安裝 GDSFactory+ 的 VS Code 終端機中，檔案會在 GDSFactory+ Layout Viewer 開啟；否則會透過 klive 傳到 KLayout。可用 `--viewer klayout` 或 `--viewer gdsfactoryplus` 明確指定。新的 cell 模組也請以相同區塊結尾：

```python
if __name__ == "__main__":
    # Imported here because orcapen_sc_pdk.pdk imports this module.
    from orcapen_sc_pdk.preview import show

    show(my_cell)
```

## 讓變更聚焦

- 在 OrcaPen 放置可重複利用的佈局與製程定義。
- 使用 GDSFactory 組合元件與佈線。
- 使用 SCGSim 準備模擬、整合求解器並分析回傳結果。
- 將私人佈局、參數與執行目錄保留在使用端專案。

新增介面前，先檢查相關既有原始碼與範例。將相關文件放在描述其公開行為的位置。

## 提交變更

在提取要求中說明變更的行為、受影響的公開介面及已執行的檢查。已儲存的科學結果應與原始模型及執行環境對應；修改教學不會重新執行結果。

套件角色請見[工作區與相關套件](home/ecosystem-workspace.md)；來源與執行期的界線請見[SCGSim 整合](features/scgsim-integration.md)；筆記本配對與部署請見[文件與網站](docs-publishing.md)。
