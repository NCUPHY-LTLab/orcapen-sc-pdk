---
title: "文件與網站"
sidebar: development
---

使用鎖定的文件環境建置網站；流程不會執行筆記本或啟動求解器。

## 本機建置

請先產生 README 與圖層片段；Quarto 會在執行 pre-render hook 前掃描這些納入的檔案。

```bash
uv sync -p 3.12 --locked --group docs --extra dev
uv run --group docs python scripts/sync_qmd_notebooks.py notebooks/src notebooks
uv run --group docs python scripts/build_overview_snippets.py
uv run --group docs quarto render docs --no-execute
uv run python scripts/check_docs_navigation.py docs/_site
```

筆記本同步命令應回報沒有差異。網站輸出位於 `docs/_site/`。本機靜態預覽可用下列命令在本機迴路介面提供已建置網站：

```bash
python -m http.server --directory docs/_site 8000 --bind 127.0.0.1
```

## 編輯筆記本指南

正式教學來源位於 `notebooks/src/`，供下載的筆記本位於 `notebooks/`。只有在配對筆記本需要更新時，才使用同步工具明確指定 `--generate`。修改可執行範例前，請確認相符的 SCGSim 版本與使用說明。

## 網站頁面與發布

可審閱的拉取請求會建置網站供審閱；`main` 分支成功建置後會發布至 [GitHub Pages](https://ncuphy-ltlab.github.io/orcapen-sc-pdk/)。網站使用 Quarto 原生導覽與 Askr 主題，詳見[主題與工具鏈](features/docs-theme.md)。

## 保存已發布文件

準備後續版本時，將各舊版本的 `docs-site.tar.gz` 加入 `docs/releases-history.json`，填入版本、標籤及該次 `SHA256SUMS` 記錄的 SHA-256。Pages 只下載清單指定的封存檔，並保存在 `vVERSION/`；Askr 版本選單會列出實際存在的文件版本。首次發布的歷史清單為空。
