---
title: "開始貢獻"
sidebar: development
---

透過[公開儲存庫](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk)貢獻可重複利用的 cell、製程紀錄、範例或文件。本頁說明如何建立工作目錄，以及一項變更如何從 Issue 走到合併的提取要求。若要撰寫 cell，請接著閱讀[什麼是 cell](contributing/what-is-a-cell.md)與[建構規則](contributing/rules.md)。

## 建立開發工作目錄

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12
```

這會安裝 PDK 與開發工具 pytest、Ruff。請執行 `uv run python --version` 確認 Python 版本。若要設定檢視工具，請參閱[預覽元件](start/preview-cells.qmd)。文件相依套件與預覽方式請見[文件與網站](docs-publishing.md)。

若 GDSFactory+ 擴充套件在 `pyproject.toml` 或 `uv.lock` 加入本機環境設定，請將這些變更保留在本機工作目錄。

## 一項變更的流程

1. **Issue。** 說明目標，以及怎樣才算完成。較大的工作、新的 cell 或公開介面的變更從這裡開始；小而明確的修正可以直接開提取要求。
2. **Issue 分支。** 在為該 Issue 建立、從 `develop` 分出的分支上工作。
3. **提取要求併入 `develop`。** 寫明對應的 Issue、變更內容，並為每個驗收項目附上證據（見[提交變更](#submit-a-change)）。
4. **審查。** 審查者依 Issue 檢查變更；若是 cell，也依[建構規則](contributing/rules.md)檢查。由 PDK 維護者合併。

## 為新 cell 加入預覽 {#preview-a-component}

使用方式與檢視工具設定請見[預覽元件](start/preview-cells.qmd)。新增 cell 模組時，在檔案末尾加入以下區塊，讓使用者能直接執行檔案並預覽指定的 cell。

```python
if __name__ == "__main__":
    # Imported here because orcapen_sc_pdk.pdk imports this module.
    from orcapen_sc_pdk.preview import show

    show(my_cell)
```

## 讓變更聚焦

- 在 OrcaPen 放置可重複利用的佈局與製程定義。
- 使用 GDSFactory 組合元件與佈線。
- cell 一律直接以 `@gf.cell` 裝飾，GDSFactory+ 只辨識這種寫法。含曲線的 cell 接收 `curve_sampling: CurveSampling = FABRICATION`，並傳給巢狀 cell 與曲線 helper；詳見[曲線取樣](usage/curve-sampling.md)。
- 使用 SCGSim 準備模擬、整合求解器並分析回傳結果。
- 將私人佈局、參數與執行目錄保留在使用端專案。

新增介面前，先檢查相關既有原始碼與範例。將相關文件放在描述其公開行為的位置。

## 提交變更 {#submit-a-change}

在提取要求中說明變更的行為、受影響的公開介面及已執行的檢查。已儲存的科學結果應與原始模型及執行環境對應；修改教學不會重新執行結果。

套件角色請見[工作區與相關套件](home/ecosystem-workspace.md)；來源與執行期的界線請見[SCGSim 整合](features/scgsim-integration.md)；筆記本配對與部署請見[文件與網站](docs-publishing.md)。

### 候選 cell

候選 cell 是尚未成為 Library 一部分的新 cell；Library 是本儲存庫 `develop` 分支所帶的已註冊 cell 集合。使用端會固定使用 `develop`，GDSFactory+ 也會列出其中的 cell，所以 `develop` 不放候選 cell：放在那裡的候選 cell 會變成別人可以依賴的東西。

候選 cell 放在它的 Issue 分支上，也就是為提出它的 Issue 所建立的分支。repository 擁有者可以把它合併到個人分支來試用；個人分支是擁有者自己用來預覽工作的分支。這裡的個人分支是公開的，所以含有私人設計的候選 cell 要改從私人佈局儲存庫開始。
