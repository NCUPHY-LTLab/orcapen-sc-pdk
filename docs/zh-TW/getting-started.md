---
title: "安裝與啟用"
sidebar: get-started
---

安裝下列公開原始碼版本、啟用 OrcaPen 製程設計套件（Process Design Kit，PDK），並建立已註冊的元件。使用佈局不需要 Palace 或 AEDT 安裝環境。

## 安裝

請在專案環境使用 Python 3.12 或 3.13。新專案可用 `uv init --python 3.12`（或 `--python 3.13`）初始化 uv 專案，再加入公開原始碼版本：

```bash
uv add "orcapen-sc-pdk @ git+https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git@aee7f8b848895f2d107f6b086310e866e8381f73"
uv run python -c "import importlib.metadata as m; print(m.version('orcapen-sc-pdk'))"
```

確認：版本命令應回報 `0.1.0.dev2`。套件選用 GDSFactory `~=9.48.0` 及其他佈局相依套件。

## 啟用並檢視元件

在 Jupyter 筆記本或 Python 腳本中使用：

```python
import gdsfactory as gf
import matplotlib.pyplot as plt
from orcapen_sc_pdk import activate

activate()
component = gf.get_component("resonator")
print(component.name)
print(component.dbbox())
component.plot()
plt.show()
```

確認：輸出會列出元件名稱與實體邊界框，並在筆記本或繪圖視窗顯示 2D 佈局。長度與實體連接埠尺寸採用微米。

若使用腳本，將範例存成 `example.py` 並執行：

```bash
uv run example.py
```

![OrcaPen 諧振器佈局。](_static/images/components/resonator.svg){width=80%}

## 選擇下一步

| 任務 | 指引 |
| --- | --- |
| 從發射器或諧振器開始 | [常用元件](start/common-cells.qmd) |
| 選擇幾何圖層與實體高度 | [圖層與堆疊](start/layers.qmd) |
| 選擇塊材或表面介面假設 | [材料與介面](start/materials.qmd) |
| 選擇 CPW 橫截面並檢查佈局介面 | [橫截面](public-pdk-examples/cross-sections.qmd) |
| 放置、連接、佈線或匯出佈局 | [GDSFactory 與 OrcaPen](public-pdk-examples/component-authoring.md) |
| 計算物理量 | [選擇模擬](notebooks.qmd) |

模擬範例各有 SCGSim 與求解器前置需求。安裝選用的模擬相依套件前，請先閱讀所選教學的環境設定。
