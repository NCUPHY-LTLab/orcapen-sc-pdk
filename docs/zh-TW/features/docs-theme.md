---
title: "主題與工具鏈"
sidebar: development
---

本網站使用公開的 `askr-html` 格式，來源為 [Askr v0.12.0 已發布版本](https://github.com/arfiligol/askr/tree/v0.12.0)。未修改的擴充功能置於 `docs/_extensions/arfiligol/askr`，包含 MIT 授權、第三方聲明及本機字型／圖示資源。擴充功能清單 `_extension.yml` 宣告版本 `0.12.0` 與 Quarto 相容範圍 `>=1.9.38 <1.11`。[已發布的擴充功能中繼資料](https://github.com/arfiligol/askr/blob/v0.12.0/_extensions/askr/_extension.yml)記錄格式及相容需求。

根目錄的 `_extensions` 符號連結指向 `docs/_extensions`，使渲染已儲存筆記本時，擴充功能的相對引用能透過既有的 `docs/notebooks` 符號連結解析。擴充功能只有一份 vendored 副本，沒有第二份；正式筆記本來源、配對方式與輸出均未變更。

使用 Quarto **1.10.19**，這是選定的穩定使用端／CI 工具鏈。請從[官方版本](https://github.com/quarto-dev/quarto-cli/releases/tag/v1.10.19)安裝，再執行 `quarto --version` 確認。若要重現擴充功能安裝：

```bash
cd docs
quarto add arfiligol/askr@v0.12.0 --no-prompt
```

審閱後以使用端檔案提交擴充功能更新；不要修改已安裝副本，也不要追蹤會移動的分支。`_quarto.yml` 選用 `askr-html`，不會替換其主題、閱讀版面寬度、字型、顏色或原生控制項。`styles.css` 僅保留本地表格溢位與圖表彈出行為。本地色彩別名遵循 Askr 的 `--qdk-border` 與 `--qdk-canvas` 設計代碼。[元件展示集](../public-pdk-examples/index.md#components-layout)使用內建行內 Image Viewer；舊版自訂 iframe 檢視器已退役。請參閱[已發布的檢視器用法](https://github.com/arfiligol/askr/blob/v0.12.0/usage/image-viewer.qmd)。

## 語言版本與儲存庫連結

網站首頁以繁體中文呈現，英文版位於 `en/`。兩種語言各有導覽與搜尋，並透過 Askr 文件所述的 [`askr.languages` 選擇器](https://arfiligol.github.io/askr/usage/languages.html)相互連結。GitHub 按鈕使用 Quarto 原生的 `website.navbar.tools`，不是本地自訂元件。

英文來源位於 `docs/`，繁體中文譯文位於 `docs/zh-TW/`。完整渲染會先將英文網站輸出至 `_site/en/`，再由 `scripts/build_bilingual_docs.py` 暫存共用主題、資源與 API 參考，並將繁體中文網站渲染至 `_site/`。產生的 API 參考與可執行筆記本維持英文版，並由繁中指引連結至英文內容。讀者內容有變更時，請同步更新對應譯文；程式碼識別符與範例應在兩個版本中保持一致。

使用現有本機 Preview 時，請以 `--profile preview` 渲染；語言連結會使用 `/` 與 `/en/`，而非部署用的專案前綴。

文件渲染會維持 `execute.enabled: false`。建置命令、筆記本配對與 Pages 部署請見[文件與網站](../docs-publishing.md)。
