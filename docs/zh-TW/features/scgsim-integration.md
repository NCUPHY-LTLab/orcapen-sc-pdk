---
title: "OrcaPen 與 SCGSim 整合"
sidebar: development
---

將所選元件的幾何、堆疊、材料與來源標註傳給教學指定版本的 SCGSim。SCGSim 負責後端準備與回傳結果；OrcaPen 提供公開模型輸入。

## 保留來源模型

幾何應保留實體圖層識別、晶粒表面、原始厚度、孔洞、放置位置與導體歸屬。非金屬定位薄片用來識別介面，不會新增金屬或指派求解器端點。

技術來源透過 `LayerLevel.info["physical_layer"]` 提供實體宣告。所選元件的取得器會新增來源所屬紀錄，但不會改變全域材料或堆疊定義。精確紀錄欄位請查閱[技術來源](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/tech.py)及所選教學的取得器。

## 為所選計算使用同一執行環境

請依照[選擇模擬](../notebooks.qmd)中的教學操作。一般後端 API 請使用與該教學版本相符的 [SCGSim 文件](https://github.com/OrPenStrike/scgsim/tree/develop/docs)。

來源準備、原生執行與回傳執行結果分析是不同操作。來源預覽只顯示幾何；若要判定模擬結果，請檢查後端的實際物件、指派與回傳量。
