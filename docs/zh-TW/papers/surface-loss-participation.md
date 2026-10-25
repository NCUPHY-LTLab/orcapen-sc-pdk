---
title: "表面損耗與參與率研究"
sidebar: research
---

選擇表面介面假設或詮釋參與率（participation）計算時，請閱讀這些參考資料。應使論文的幾何、材料與擷取方法符合所用模型。

| 參考資料 | 閱讀重點 |
| --- | --- |
| Wenner et al., “Surface loss simulations of superconducting coplanar waveguide resonators,” APL 99, 113513 (2011), [DOI](https://doi.org/10.1063/1.3637047) | MA/MS/SA 介面分類與表面損耗尺度關係 |
| Woods et al., “Determining Interface Dielectric Losses in Superconducting Coplanar-Waveguide Resonators,” PRApplied 12, 014012 (2019), [DOI](https://doi.org/10.1103/PhysRevApplied.12.014012) | 介面損耗擷取與材料／製程假設 |
| Wang et al., “Surface participation and dielectric loss in superconducting qubits,” APL 107, 162601 (2015), [DOI](https://doi.org/10.1063/1.4934486) | Transmon 表面參與率與幾何依賴性 |
| Lahtinen and Möttönen, “Effects of device geometry and material properties on dielectric losses in superconducting coplanar-waveguide resonators,” JPCM 32, 405702 (2020), [DOI](https://doi.org/10.1088/1361-648X/ab98c8) | 幾何、材料屬性不確定性與反向詮釋 |

## 為計算選擇假設

記錄介面角色、厚度、介電常數與損耗正切，並註明各數值在來源中是量測、擬合或假設而得。比較製程時，亦應記錄金屬、基板、表面處理、溫度與頻率。

目前公開紀錄位於 [materials.json](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/materials.json)，並由 `get_interface_preset_records()` 回傳。請使用[材料與介面](../start/materials.qmd)選擇紀錄；若製程不相符，文獻慣例不會自動成為預設值。

可用教學請接續閱讀[參與率與表面損耗](../simulation/requirements/epr-loss.qmd)。
