---
title: "文件與網站"
sidebar: development
---

在 `docs/` 編輯英文讀者文件，在 `docs/zh-TW/` 編輯繁中譯文，並在 `notebooks/src/` 編輯正式教學來源。使用 Quarto 1.10.19 完整渲染時，會建置繁體中文與英文兩種網站版本；此流程不執行筆記本，也不啟動求解器。

## 在本機建置

```bash
uv sync -p 3.12 --locked --group docs --extra dev
just docs
```

確認：產生的筆記本輸入與其 QMD 來源相符，網站則出現在 `docs/_site/`。預先渲染步驟會使用 quartodoc 產生 API 參考。

本機預覽請執行：

```bash
just serve-docs
```

確認：開啟 `http://127.0.0.1:8000`，預設顯示繁體中文；英文版位於 `/en/`。檢查桌面版導覽及窄螢幕下收合的選單。

此命令會先以本機語言連結建置兩個版本，再啟動靜態伺服器。修改後執行 `quarto render docs --profile preview --no-execute`，並重新整理瀏覽器。

## 編輯筆記本但不改變結果

QMD 檔案是教學文字、可執行儲存格、設定與穩定程式碼儲存格 ID 的來源。對應的 IPYNB 是產生後供下載的檔案。修改 QMD 後，使用既有配對工具重新產生對應筆記本；全儲存庫轉換請使用 `just convert-notebooks`。

`just check-notebooks` 會比較來源結構而不執行儲存格。模擬執行應與網站建置分開處理。

## 頁面與下載

可審閱的拉取請求（Pull Request，PR）會建置網站，草稿（Draft）則略過建置；`main` 分支成功建置後會部署至 [GitHub Pages](https://ncuphy-ltlab.github.io/orcapen-sc-pdk/)。

SurfaceBands 範例從其正式 QMD 路徑渲染，讓相鄰 HTML 連結與模型 JSON 保持在一起。其 IPYNB 則是獨立下載檔。既有的渲染後輔助程序會逐位元組複製兩個原始 QMD 來源到網站輸出；原始檔下載錨點使用 `data-noresolveinput`。

## 主題與網站結構

網站使用未修改的 Askr 擴充功能與 Quarto 原生導覽。所選版本請見[主題與工具鏈](features/docs-theme.md)。頁面分置於入門、模擬、API、研究或開發五個區域；標誌會返回首頁。

API 定義請以[公開套件原始碼](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk)為準；文獻筆記請見[研究](paper-review.md)。
