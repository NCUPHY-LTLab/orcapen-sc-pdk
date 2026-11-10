---
title: "安裝與入門"
sidebar: get-started
---

安裝公開原始碼預覽版，啟用其 GDSFactory 製程設計套件（Process Design Kit，PDK），並建立已註冊的諧振器。建立佈局不需要求解器。

有 GDSFactory+ 授權時，可在本機或遠端開發並預覽版圖。沒有授權時，請使用本機 KLayout 流程。設定方式請見[預覽元件](start/preview-cells.qmd)。

## 安裝

請搭配 uv 使用 Python 3.12 或 3.13。建立 Python 3.12 專案時：

{{< include _includes/_readme-install.md >}}

若使用既有專案，請執行：

```bash
uv add "orcapen-sc-pdk @ git+https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git@947a216d295d3ceadd1dc06bcd34e8aebf61ff0c"
uv run python -c "import importlib.metadata as m; print(m.version('orcapen-sc-pdk'))"
```

::: {.callout-note title="套件中繼資料不代表正式發布"}
版本命令會回報 `1.0.0`，也就是此預覽原始碼中的套件中繼資料版本；這不代表 `v1.0.0` 已正式發布。
:::

## 啟用並建立元件 {#activate-and-see-a-cell}

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate

activate()
component = gf.get_component("resonator")
print(component.name, component.dbbox())
component.plot()
```

輸出會包含諧振器名稱與邊界框，並顯示 2D 佈局。實體尺寸單位為微米。

## 接續閱讀

先從[常用元件](start/common-cells.qmd)選擇要查看的版圖，再依照[預覽元件](start/preview-cells.qmd)設定 GDSFactory+ 或本機 KLayout。接著可參閱[圖層與堆疊](start/layers.qmd)及[材料與介面](start/materials.qmd)。各[模擬指南](notebooks.qmd)會列出其 SCGSim 版本與求解器需求。
