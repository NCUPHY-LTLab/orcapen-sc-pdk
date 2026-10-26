# 曲線取樣（Curve sampling）

使用同一個 OrcaPen 元件，依用途選擇製程或模擬的曲線點數。設定會傳入巢狀元件，並納入元件快取（cell cache）的身分。

## 選擇設定

中央入口是 `orcapen_sc_pdk/curve_sampling.py`。專案可在自己的設定檔保存一組數值，再於建立元件時套用，無須複製 PDK 元件。

| 設定檔（profile） | 完整圓的基準線段數 | 預設用途 |
| --- | ---: | --- |
| `fabrication` | 256 | 預設製程版圖 |
| `simulation` | 依直徑選擇 16、24 或 32 | 模擬幾何候選 |

`simulation` 依每一個圓形邊界的直徑 D 分級；圓弧使用對應完整圓的直徑，並按角度分配線段。

| 直徑 D（µm） | 完整圓基準線段數 |
| --- | ---: |
| D < 20 | 16 |
| 20 ≤ D < 100 | 24 |
| D ≥ 100 | 32 |

W6/G7 圓頭金屬的直徑為 6 µm，因此半圓使用 8 段、9 個頂點；外圈開口的名義直徑為 20 µm，使用 12 段、13 個頂點。開口保留原本的多邊形偏移（polygon offset）形狀，不是重新擬合的理想圓。圓頭與圓角矩形的金屬及開口各自按半徑選級距；明確指定局部點數時仍沿用指定值。

⚠️ 模擬效果尚待驗證；目前依 Human 肉眼判斷，預期不致對網格生成（meshing）造成過多負擔。

```python
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.cells import circular_pad_capacitor
from orcapen_sc_pdk.curve_sampling import curve_sampling

activate()

with curve_sampling("simulation"):
    coarse = circular_pad_capacitor(outer_radius_um=100)

with curve_sampling("fabrication"):
    fine = circular_pad_capacitor(outer_radius_um=100)

print(coarse.info["curve_sampling"])
```

同一個程序切換設定時，不必清除快取。再選回相同參數與取樣設定，會重用該設定的快取元件。

## 覆寫與重現

每個 OrcaPen cell 都接受 `curve_sampling=(點數, 最大弦高誤差)`。優先順序是元件明確指定、外層設定區塊、製程預設。元件指定的設定也會傳給其子元件；子元件若再明確指定，則以子元件的設定為準。

```python
# 固定完整圓 64 段。
component = circular_pad_capacitor(
    outer_radius_um=100,
    curve_sampling=(64, None),
)
```

點數須為至少 4 的四倍數，使圓在四個軸向都有頂點。數字指布林運算前完整圓不重複的頂點／線段數；資料庫單位（DBU）量化可能合併頂點，布林交點則可能增加頂點。

分享設定時，一併記錄 PDK 的來源提交（source commit）、元件參數、取樣 tuple、明確的局部覆寫，以及匯出 GDS 的雜湊。`component.info["curve_sampling"]` 記錄的是基準設定；依直徑分級時，`points_per_circle` 為 `None`，級距記錄在 `diameter_tiers_um`。實際多邊形頂點數應由產出的 GDS 讀回。

## 依半徑增加點數

tuple 的第二欄可指定理想圓內接多邊形的最大弦高誤差（sagitta），單位為 µm。例如 `(32, 0.05)` 表示至少 32 段，必要時依半徑增加點數。`0.05` 只是呼叫格式示例，請依自己的幾何需求選值。

對半徑 (R\) 與完整圓線段數 (N\)，弦高為 (e=R[1-\cos(\pi/N)]\)。實作使用等價且較穩定的反三角公式求點數，再向上取四的倍數。

```python
from orcapen_sc_pdk.curve_sampling import circle_segments

settings = (32, 0.05)
print(circle_segments(radius=350, sampling=settings))
```

直徑 700 µm 的理想圓，32 段的弦高約 1.685 µm，256 段約 0.02635 µm。這個計算適用於量化前的理想圓；點數不是求解精度或製程公差的保證。

## 涵蓋範圍與局部覆寫

| 幾何路徑 | 取樣方式 |
| --- | --- |
| 圓、完整圓環、Kosen arm-head、TSV 圓形邊界 | 中央完整圓點數；圓環的內外半徑分別套用相同規則 |
| 圓弧、圓弧 bend | 按角度分配線段數，包含兩個端點 |
| IDC 圓角、圓頭金屬、圓角矩形 | 按實際半徑及角度取樣，保留切面與端點 |
| Euler path／bend | 將中央設定換算成 GDSFactory 的 `npoints` 預算；GDSFactory 另行分配 Euler／圓弧段，因此最終點數不同 |
| 八方向路由 | 中央角度步距；既有 Euler 積分保留額外細分 |
| 插值樣條與 B-spline | 保留原本的 `samples_per_span`，完整圓點數不定義任意樣條的誤差 |

既有明確指定的 `npoints`、`angular_step`、`bend_npoints`、`n_cap_points`、`n_corner_points` 或路由角度步距，優先於中央規則。使用外部自訂 bend 時，請由該 bend 提供自己的取樣設定與長度契約。

GDSFactory 的 bend `info["length"]` 仍保留離散中心線長度；PDK 的 `design_length_um` 是解析設計長度。Resonator 與 Purcell 的長度配置採用設計長度，避免因取樣點數改變而移動端點。Purcell 沿用原有一個 DBU 的長度比較，改以整數格點運算，DBU 本身不變。

既有 GDS 不會因切換設定而改變。要產生另一種解析度，請由相同元件參數重新建立並另外匯出。
