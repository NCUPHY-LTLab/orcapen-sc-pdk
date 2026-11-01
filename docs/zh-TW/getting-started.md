---
title: "安裝與入門"
sidebar: get-started
---

安裝 OrcaPen SC PDK 1.0.0，啟用其 GDSFactory 製程設計套件（Process Design Kit，PDK），並建立已註冊的諧振器。建立佈局不需要求解器。

## 安裝

請搭配 uv 使用 Python 3.12 或 3.13。建立 Python 3.12 專案時：

{{< include _includes/_readme-install.md >}}

若使用既有專案，請執行：

```bash
uv add "orcapen-sc-pdk @ git+https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git@v1.0.0"
uv run python -c "import importlib.metadata as m; print(m.version('orcapen-sc-pdk'))"
```

確認：`v1.0.0` 原始碼標籤可用後，版本命令會回報 `1.0.0`。

## 啟用並建立元件

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate

activate()
component = gf.get_component("resonator")
print(component.name, component.dbbox())
component.plot()
```

確認：輸出包含諧振器名稱與邊界框，並顯示 2D 佈局。實體尺寸單位為微米。

## 接續閱讀

請參閱[常用元件](start/common-cells.qmd)、[圖層與堆疊](start/layers.qmd)、[材料與介面](start/materials.qmd)或[模擬指南](notebooks.qmd)。各模擬指南會列出其 SCGSim 版本與求解器需求。
