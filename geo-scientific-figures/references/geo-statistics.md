# 地学统计图与模型验证

统计面板用 `style_stat_ax()`，成组图在 `rc_context()` 中共享预设。先明确样本、单位、统计口径和观测覆盖，再画坐标、数据和结果。用淡灰参考线辅助读数，把系列图例移到独立槽或图外。

## 精度验证散点和密度图

1. 按样点、时间和匹配窗口配对观测与估计。单位和尺度统一，记录有效配对数。受同一地块、站点或场景影响的样本需保留分组关系。
2. x 轴为参考或观测值，y 轴为估计或反演值。两轴使用共同上下界和等比例刻度。`1:1` 虚线指示一致，OLS 实线表达估计对观测的线性关系。
3. 少量点直接绘制，堆叠明显时用 hexbin 或密度着色点。`mode="auto"` 在有效点数超过 5,000 且值域有跨度时用 hexbin；`mode="density"` 用方形分箱计数着色。比较密度面板时统一网格和 `norm`，注明原始点数、权重和色条单位。
4. 指标框使用同一位置与数值精度。面板数据占据角落时换 `stats_loc`，或关闭内嵌框后把指标放入专用图注或统计槽。图例说明 1:1 与 OLS 的线型，避开数据和指标。

设参考值为 \(x_i\)，估计值为 \(y_i\)，误差 \(e_i=y_i-x_i\)。工具函数返回以下指标。

| 指标 | 定义和解释 |
| --- | --- |
| `N` | 有效配对数，保留有效的零值 |
| `R2` | \(1-\sum e_i^2/\sum(x_i-\bar{x})^2\)，针对原始估计，可为负。参考方差为零时显示 `NA`，不绘制 OLS |
| `RMSE` | \(\sqrt{\operatorname{mean}(e_i^2)}\)，原量纲 |
| `MAE` | \(\operatorname{mean}(|e_i|)\)，原量纲 |
| `Bias` | \(\operatorname{mean}(e_i)\)，正值表示整体高估 |

论文如使用 Pearson \(r^2\) 或回归拟合的决定系数，单独计算并在图注写明定义。不要把回归线拟合优度混入原始预测精度。单位由数据元数据确认，训练与测试条件、空间/时间分割和抽样方法写入图注或正文。

```python
from geo_fig_kit import add_aligned_colorbar, plot_validation_scatter, style_stat_ax

points, stats = plot_validation_scatter(ax, reference, estimate, mode="hexbin", unit="K")
style_stat_ax(ax)
add_aligned_colorbar(fig, points, ax, label="Paired samples per bin")
fig.legend(*ax.get_legend_handles_labels(), loc="upper right", frameon=False, ncols=2)
```

示例中的图例需要预留顶部空间。分组验证可共享坐标范围，展示各组样本量与指标。空间集簇、着色截尾或落在显示框外的数据量需在结果解释中说明。

## 分组柱状图、基线与消融

- `make_grouped_bar()` 输入顺序为类别、按系列组织的数值、系列名称。相同方法在所有面板对应同一颜色和 hatch。默认黑色描边为 0.6 pt。
- 根据柱高、误差线和注值动态分配范围，保留零基线。正值图从 0 起，含负值的图同时覆盖正负。差异很小时可另画点图、误差线图或差值图。刊方允许断轴等特殊设计时，显式标示断点并在图注交代。
- 保留负值，标注从对应柱端向外排。范围留出数字高度；密集时减少小数位、拆分面板或只标关键差值。缺失值保留空位，图注说明缺失，别补成 0。
- 多指标并排时采用独立子图与单位，便于处理 RMSE、MAE、相关性、耗时等不同量纲。尽量共享类别顺序、语义色、图例和同义指标的 y 范围。避免用双 y 轴对比方法。
- 类别名过长时优先按语义换行，或使用短代码并在图注列出全称。类别很多时拆分面板或用水平分组柱图。少量英文长标签可倾斜约 30° 并右对齐，渲染后检查标签间距和画布边缘。
- 用 `(高值 − 参考值)` 或按明确定义计算相对改进，并写明方向。误差线应说明 SD、SE、置信区间或交叉验证分布，样本量和重复单位须一致。

```python
from geo_fig_kit import make_grouped_bar, style_stat_ax

make_grouped_bar(ax, ["Upland\nforest", "River\nterrace", "Coastal\nwetland"],
                 [[0.73, 0.79, 0.75], [0.68, 0.77, 0.71]],
                 ["Full", "Without terrain"], ylabel="F1 score",
                 hatch_patterns=("", "//"), annotate=True, fmt="{:.2f}")
style_stat_ax(ax, grid_axis="y")
```

## 时空趋势、差异与不确定性

- 以真实时间排序，用日期定位器减少重复标签，明确时间尺度、单位、季节窗口和时区约定。大缺口保留断线。避免以滚动平均代替数据采样频率或不确定性。
- `make_trend()` 支持每条序列一组非负对称误差幅度，并用 `fill_between` 绘制。使用 `None` 表示该系列不带误差。非对称上下限可在函数绘制曲线后自行填充。注明阴影含义与区间覆盖水平。
- 同轴优先保留能回答问题的 3–5 条主曲线。系列更多、置信带过密时按区域或指标分面，用线型或标记辅助辨识。长时间序列精简时间刻度，只标有解释作用的时间节点。
- 栅格区域均值要处理有效面积与 NoData。规则经纬网可根据网格条件用纬度余弦近似，精确分析使用像元真实面积。可先将多边形与格网求交，按覆盖率和像元面积加权。逐时刻同步报告有效覆盖率或其阈值。
- 在面板副标题、留白处或独立结果栏标注斜率、时间单位、置信区间和实测 `p` 值，例如 `Slope = +0.003 NDVI yr⁻¹, p = 0.018`。图注写明估计和检验方法、显著性阈值以及多重比较校正口径。先核查季节性、序列自相关和有效样本量，并采用与数据生成过程相符的检验。`make_trend()` 负责绘制数据及传入的区间。

```python
from geo_fig_kit import make_trend, style_stat_ax

lines = make_trend(ax, dates, [regional_mean, baseline], ["Study area", "Reference area"],
                   y_err=[regional_ci_halfwidth, None], xlabel="Year", ylabel="NDVI")
lines[1].set_linestyle("--")
style_stat_ax(ax, grid_axis="y")
```

### Dedicated Legend Panel

多张趋势图重复同一组系列时，可在 `GridSpec` 底部跨列预留一整行。用同一语义色和线型，从数据面板按顺序收集图例项，将单独一行的坐标轴关闭。若差异带有共同含义，可加一个独立代理图例项说明阴影。预留足够的行高用于换行。

```python
import matplotlib.pyplot as plt

fig = plt.figure(figsize=size, layout="constrained")
grid = fig.add_gridspec(2, 2, height_ratios=(1, 0.18))
data_axes = [fig.add_subplot(grid[0, index]) for index in range(2)]
legend_ax = fig.add_subplot(grid[1, :])

# 在 data_axes 中绘制已命名的序列后，再共享图例。
by_label = {}
for data_ax in data_axes:
    handles, names = data_ax.get_legend_handles_labels()
    for name, handle in zip(names, handles):
        by_label.setdefault(name, handle)
legend_ax.set_axis_off()
if by_label:
    legend_ax.legend(list(by_label.values()), list(by_label), loc="center",
                     ncols=min(3, len(by_label)), frameon=False)
```

## 矩阵热力图和混淆矩阵

| 图型 | 色表与轴 | 图注应注明 |
| --- | --- | --- |
| 分类混淆矩阵 | 顺序色表，通常行是参考，列是分类结果 | 原始计数、按行归一化或按列归一化，以及基数 |
| 相关、异常或差异矩阵 | 负正发散色表，用 `center_zero=True` 居中 | 相关类型和样本数，或异常参考值及单位 |
| 缺测单元 | 专用灰色或透明，不参与颜色缩放或数值标注 | 无样本、掩膜或未估计的定义 |

- 类别顺序在两轴与正文一致。按参考类别归一化时，生产者精度（PA）为对角元素除以该参考类总数。按预测类别归一化时，用户精度（UA）为对角元素除以该预测类总数。参考在行、预测在列时，分别除以行和与列和。若报告面积加权精度，先按抽样设计构建加权误差矩阵，再用相同定义计算。[土地变化精度评估方法](https://doi.org/10.1016/j.rse.2014.02.015)
- 空类别的归一化比值写成缺失，零计数保留 0。报告基数或有效样本数，对照图统一 0–1 或 0–100%。在混淆矩阵用细轮廓标出有效对角单元，保留错分单元的颜色可读性。相关性矩阵优先统一 −1 至 +1，以 0 为中性色，对角线可保留作定位或在图注中说明省略。
- `make_heatmap()` 按单元的感知亮度选黑或白字。只在文字清晰时注值。较大矩阵可只标关键单元、增设类别代码或使用正文表格。
- 调整 `image.set_clim()` 会改变标注背景色。需要固定范围且添加文字时，应在确定最终 `norm` 后作对比检查并更新标注颜色。发散矩阵按有物理意义的正负范围比较，不同变量之间保留单独量纲。

```python
import numpy as np
from matplotlib.patches import Rectangle
from geo_fig_kit import make_heatmap, style_stat_ax

counts = np.array([[54, 6, 0], [2, 38, 3], [4, 3, 20]])
total = counts.sum(axis=1, keepdims=True)
normalized = np.divide(counts, total, out=np.full(counts.shape, np.nan), where=total > 0)
labels = ["Forest", "Cropland", "Water"]
image, colorbar = make_heatmap(ax, normalized, labels, labels, cbar_label="Reference-class share",
                               annotate=True, fmt="{:.0%}")
image.set_clim(0, 1)
for index, value in enumerate(np.diag(normalized)):
    if np.isfinite(value):
        ax.add_patch(Rectangle((index - 0.5, index - 0.5), 1, 1, fill=False,
                               edgecolor="0.32", linewidth=0.55, clip_on=False))
style_stat_ax(ax)
ax.set(xlabel="Predicted class", ylabel="Reference class")
```

## 区域与地类的分布对比

| 图型 | 适用问题 | 需要标明 |
| --- | --- | --- |
| 箱线图 | 比较区域的中位数、四分位距和尾部 | 箱须规则、离群点定义、每组有效 `n` |
| 小提琴图 | 比较地类内部的偏态、长尾或多峰 | 密度估计、带宽、样本量和宽度含义 |
| 脊线图 | 按地类、海拔带或月份观察多组分布移动 | 共用 x 轴、密度归一化、统一组间偏移和组顺序 |

- 每组先保留有效的 0，再去除掩膜与非有限值。说明统计单位是像元、样点还是地块。区域面积、抽样权重或空间自相关显著时，选用符合分析目的的抽样、面积加权或独立地块汇总。
- 箱线图适合较紧凑的论文版面，样本很少时可叠加原始点。小提琴图使用 `ax.violinplot(samples, showmedians=True)`；检查带宽敏感性和物理边界，常数或稀少样本改用点与中位数。用于对照时固定数据轴和密度估计口径。
- 脊线图可用共用的直方图箱边绘制。所有组使用相同的密度缩放和垂直偏移，纵向间距用于排布类别。各组密度积分为 1 时，用标签单独报 `n`。

```python
import numpy as np
from geo_fig_kit import style_stat_ax

# samples 是已清理的非空一维数组列表，labels 按图中顺序对应各组。
pooled = np.concatenate(samples)
# 全部样本同值时改用点标注，避免零宽分箱。
edges = np.linspace(pooled.min(), pooled.max(), 22)
densities = [np.histogram(group, bins=edges, density=True)[0] for group in samples]
height_scale = 0.85 / max(density.max() for density in densities)
for row, density in enumerate(densities):
    ax.stairs(row + density * height_scale, edges, baseline=row, fill=True,
              facecolor="#CFDFEC", edgecolor="#175181", linewidth=0.65)
ax.set_yticks(range(len(labels)), [f"{label} (n={len(group)})" for label, group in zip(labels, samples)])
style_stat_ax(ax)
```
