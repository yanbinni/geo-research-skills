# 地图与统计复合图及交付验收

## 面板、共享元素和阅读顺序

先确认读者需要看到哪些空间关系、比较结果和不确定性，再安排主图、概况图与统计辅助图。为较宽地图、标注密集的面板和独立图例预留空间，按左到右、上到下编号。双栏空间不足时可改上下布局，或拆出补图。

| 构图 | 推荐做法 |
| --- | --- |
| 地图 + 验证图 | 地图采用封闭框；散点共享 x/y 数值范围并设等比例。地图值色条与点密度色条各自注明量纲 |
| 多时相地图 + 区域时序 | 同一地理窗口、网格与对照色标，时间轴明确标出各地图对应日期 |
| 多时相 / 多算法网格 | 行列对应时间或算法；统一可比地图的范围、投影、`norm` 和色表，以一条色条跨行或跨列 |
| 地图 + 右侧纬向均值剖面 | 沿每个纬带的经度方向求均值；剖面 x 为均值、y 为纬度，同地图共享纬度 y 轴及其绘图区边界 |
| 研究区主图 + 多样区局部放大 + 精度验证 | 主图跨行，放大图在右上网格，验证图位于右下。主图用框或编号对应各样区 |

- 创建 figure 时优先用 `layout="constrained"`，等价于 `constrained_layout=True`。复杂 inset、独立色条或组间空隙可由显式 `GridSpec` 控制；地图和统计需要独立子网格时用 `fig.subfigures()`。避免末尾调用 `tight_layout()`，它会关闭 constrained 布局并重新分配已按固定纵横比安排的空间。[Matplotlib 布局指南](https://matplotlib.org/stable/users/explain/axes/constrainedlayout_guide.html)
- 用同一 `rc_context()` 初始化所有面板。地图与统计分别调用 `style_map_ax()` 和 `style_stat_ax()`；锁定编号字体、大小、锚点和点距。
- 用 `GridSpec` 配置跨列面板和实际宽高比例。固定纵横比的地图或散点绘图区可能小于其 subplot 槽位，最终对齐以画布绘制后的轴边界为准。
- 锁定目标成品宽度。由各地图的实际投影显示比例和色条、刻度所占空间反推净高，再加最小必要边距。并排底部的色条或图例统一对齐，预留视觉上均衡的空间。
- 单面板色条用 `add_aligned_colorbar()`。其 `size` 可用相对比例或英寸，`pad` 为英寸。溢出箭头占用色条自身长度。跨面板共用时优先给 `fig.colorbar(..., cax=...)` 分配独立 `GridSpec` 槽，再核对颜色、`norm`、单位、刻度和 `extend` 一致。共用色条基于相同物理变量、单位和归一化。
- 相邻面板呈现不同物理变量且各自用色条时，使用不同实际色表。对称发散色条采用双尖端 `extend="both"` 或平端 `extend="neither"`，并协调邻接面板的端部形态。详细规则见 [版式与导出](style-and-export.md)。
- 给重复图例预留跨列空轴，按 [Dedicated Legend Panel](geo-statistics.md#dedicated-legend-panel) 收集并去重，统一顺序和标记含义。

### 三种地学复合布局

1. **多时相或多算法网格。** 先创建一份颜色归一化对象，传给每个 `imshow()`，并使用同一实际色表。地图轴设相同投影和范围，时间或算法标签放在行列边缘。网格可用 `fig.colorbar(images[0], ax=list(map_axes.flat), location="right")` 生成一条共享色条，或在 `GridSpec` 末列预留 `cax`。显示范围截断时由共享色条标示 `extend`。
2. **地图与右侧纬向均值剖面。** 规则经纬网以数据轴 y 的纬度为共同坐标。按纬带从有效像元计算沿经度的均值，按像元面积或覆盖率加权。两轴 `sharey`，同时检查绘图区顶部和底部实际对齐。对投影米轴或曲线纬线，可用共同纬度网格重绘，或给剖面独立轴并标明对应纬带。
3. **研究区、局部放大和验证。** 例如 `GridSpec(2, 3, width_ratios=(1.45, 1, 1))`，主图占 `grid[:, 0]`，两个放大图占 `grid[0, 1]` 和 `grid[0, 2]`，验证图占 `grid[1, 1:]`。主图框、放大图标题和样区名称相互对应，局部边框和连接线遵循 [地图制图](cartography-core.md)。局部影像只有在量纲、拉伸和 `norm` 一致时共享色条。

以下写法让绘图区在固定纵横比下仍共享纬度的物理高度。`values` 为规则经纬度栅格，首行为最北侧。示例中掩膜仅表示窗口内缺测，`lat_centers` 按同一顺序对应到像元中心。示例采用相同的整像元经度跨度，不等面积或分区边缘用核实后的权重。

```python
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
from geo_fig_kit import format_lonlat_ticks, get_cmap_safe, style_map_ax, style_stat_ax

# fig、ax_map 来自使用固定边距、底部预留色条空间的普通 Matplotlib 画布。
field = np.ma.masked_invalid(np.ma.asarray(values, dtype=float))
palette = get_cmap_safe("viridis").with_extremes(bad="#D9D9D9")
image = ax_map.imshow(field, extent=(west, east, south, north), origin="upper",
                      cmap=palette, rasterized=True)
ax_map.set_aspect(1 / np.cos(np.deg2rad((south + north) / 2)))
style_map_ax(ax_map)
format_lonlat_ticks(ax_map)

divider = make_axes_locatable(ax_map)
ax_profile = divider.append_axes("right", size="40%", pad=0.18, sharey=ax_map)
ax_profile.plot(field.mean(axis=1), lat_centers, color="#175181")
ax_profile.set_xlabel(f"Zonal mean ({unit})")
style_stat_ax(ax_profile, grid_axis="y")
ax_profile.tick_params(axis="y", labelleft=False)
ax_map.set_ylim(south, north)
fig.canvas.draw()
map_bounds = ax_map.get_position()
gap, bar_height = np.array([0.34, 0.08]) / fig.get_figheight()
cax = fig.add_axes((map_bounds.x0, map_bounds.y0 - gap - bar_height, map_bounds.width, bar_height))
fig.colorbar(image, cax=cax, orientation="horizontal", label=unit)
```

剖面与主图使用同一个 divider。色条按渲染后的实际地图宽度定位。更改画布尺寸或边距后重新定位色条，并复核纬度对齐。

## 复合图示例

以下示例使用合成场和合成观测来演示布局。实际任务先用 `inspect` 核对地理输入。它使用普通经纬度轴，无需 Cartopy，主图有发散色标，验证图分别保存 `1:1` 和 OLS 线型。

```python
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import MultipleLocator
from geo_fig_kit import (PRESETS, add_aligned_colorbar, add_panel_label, apply_preset,
                         format_lonlat_ticks, get_cmap_safe, plot_validation_scatter,
                         save_figure, style_map_ax, style_stat_ax)

rng = np.random.default_rng(21)
u, v = np.meshgrid(np.linspace(-1, 1, 180), np.linspace(1, -1, 180))
change = np.ma.masked_where(u ** 2 + v ** 2 > 1.55, 1.5 * np.sin(2.3 * u) * np.cos(1.5 * v))
observed = rng.uniform(285, 305, 280)
predicted = 0.96 * observed + 12 + rng.normal(0, 1.1, observed.shape)

with mpl.rc_context():
    preset = "journal-en"
    size = apply_preset(preset, "double", aspect=0.54)
    linewidth = PRESETS[preset]["linewidth"]
    fig, (ax_map, ax_stat) = plt.subplots(1, 2, figsize=size)
    fig.subplots_adjust(left=0.095, right=0.97, bottom=0.16, top=0.82, wspace=0.55)

    image = ax_map.imshow(change, extent=(110, 112, 31, 33), origin="upper",
                          cmap=get_cmap_safe("vik").with_extremes(bad="none"),
                          norm=TwoSlopeNorm(vmin=-1.5, vcenter=0, vmax=1.5), rasterized=True)
    ax_map.set_aspect(1 / np.cos(np.deg2rad(32)))
    ax_map.xaxis.set_major_locator(MultipleLocator(1))
    ax_map.yaxis.set_major_locator(MultipleLocator(1))
    style_map_ax(ax_map, linewidth=linewidth)
    format_lonlat_ticks(ax_map)
    colorbar = add_aligned_colorbar(fig, image, ax_map, label="LST anomaly (K)")
    colorbar.outline.set_linewidth(linewidth)

    _, stats = plot_validation_scatter(ax_stat, observed, predicted, unit="K")
    style_stat_ax(ax_stat, linewidth=linewidth)
    fig.canvas.draw()
    top = ax_map.get_position().y1
    slot = ax_stat.get_position(original=True)
    ax_stat.set_position((slot.x0, slot.y0, slot.width, top - slot.y0))
    ax_stat.set_anchor("N")
    fig.legend(*ax_stat.get_legend_handles_labels(), loc="upper right", bbox_to_anchor=(0.97, 0.97),
               frameon=False, ncols=2)
    add_panel_label(ax_map, "a")
    add_panel_label(ax_stat, "b")
    save_figure(fig, "out/map-and-validation", ("png", "pdf", "svg"))
    plt.close(fig)
```

## 必查的 8 项 Visual QA

打开 `*.preview.png`，在成品宽度检查整体，再放大检查边缘字体、连接线、掩膜和网格。按成品格式再渲染至少一次，布局或色标有调整就重新导出并查看。

| 项目 | 通过条件 |
| --- | --- |
| 1. 坐标刻度 | 经纬、日期及单位无重叠、无截断、无重复标签；方向和范围正确 |
| 2. 色条高度、范围与色表 | 纵色条等高或横色条等宽，共享色条对应目标图组。核对 `norm`、中点和上下限。不同变量的邻接面板色表不撞色，对称发散色条两端齐平或双尖，尖端无单侧失衡 |
| 3. NoData 与 0 | 外部纯白或透明并省略图例。连续图内部显著缺测用浅灰与图注说明，底部无孤立 NoData 框。离散类别的内部 NoData 在原图例末项。有效 0 与两类掩膜可区分 |
| 4. 影像拉伸明暗 | 阴影细节与亮部都有层次，同类图按承诺共用阈值与 gamma；检查硬边、空瓦片和错位 |
| 5. 辅助元素遮挡 | 图例、比例尺、指北针、小图和可选统计框避开关键数据。比例尺与真北方向在当前位置有效 |
| 6. 中英文及负号 | 中文、拉丁字母、单位、度符号和坐标负号均正确，无方框、缺字和截断 |
| 7. 子图、编号与留白 | 按阅读顺序标 `(a)`、`(b)`、`(c)`，编号同字号同锚点。对齐绘图区和旁侧剖面，检查外围白边是否过多、底部色条与图例是否对齐和视觉均衡 |
| 8. 分辨率与体积 | 检查 PNG 宽高和有效 DPI、PDF 页面尺寸及格式体积；矢量过大时定位密集图层 |

另核对数据口径和地理正确性。确认图注写明变量、时间、单位、基准和统计方法，检查 CRS、地标、边界线型、底图来源与审图信息。检查验证轴同范围同尺度、柱状图保留基线，以及灰度和色觉缺陷预览下的可读性。

## 核查文件与修复

1. 确认输出存在且可打开。PNG 的像素宽高约等于 `figsize × dpi`；PDF `MediaBox` 除以 72 得英寸；SVG `width`、`height` 和 `viewBox` 与画布匹配。检查最终贴入 Word 或幻灯片的视图。
2. PDF 可用 `pdfinfo` 核查页尺寸、`pdffonts` 查看字体、`pdfimages -list` 查看嵌入位图。打开 SVG 查找 `<text>` 和 `<image>`，检查数据区域已经适当栅格化，文字、边界与关键线条仍保留原输出特性。
3. 大于 15 MB 的矢量文件先定位密集层，选择合理的显示分辨率或设置 `rasterized=True` 后重新导出。样本密度和色块面积仍需保留统计含义。
4. 修复后重新打开预览和目标文件。交付图、绘图代码和数据出处说明，列出宽×高、DPI、色表、归一化或掩膜规则、关键指标定义和仍需确认的数据条件。

### 常见问题速修

| 预览现象 | 修复 |
| --- | --- |
| 边框刻度相撞或截字 | 降低刻度密度、精简格式或增大对应边距；类别长名可换行 |
| 色条比图面长、短或跨图不一致 | 单轴使用对齐色条，共享色条用单独 `cax`；统一 `norm`、刻度和单位后检查实际边界 |
| 不同变量撞色或发散色条一端尖一端平 | 核对实际回退色表，改用不同色表。任一端截断的对称发散色条用 `extend="both"`，端点能覆盖全值时用 `extend="neither"` |
| 无数据与零值看起来一样，或底部出现孤立 NoData 框 | 分开外部白色或透明掩膜和内部缺测。连续图将浅灰缺测的含义移入图注。分类图将内部 NoData 放到原有图例末项 |
| 影像过暗、过曝或时相对照色调跳变 | 复核有效像元分位数与缩放后调整 gamma，对照组固定阈值和亮度处理 |
| 图例、尺度、北箭头或统计框挡住有效数据 | 移入预留空槽。尺度或箭头移动后按新锚点重算距离和方向 |
| 中文变方框，坐标负号缺字 | 运行 `doctor` 确认回退字体，对照 `axes.unicode_minus=False` 后重渲染目标格式 |
| 编号上下错位或纬度剖面错行 | 以 `draw()` 后的实际轴位置对齐，核对共享纬度方向与落点，再复查编号锚点 |
| 外围白边过宽或底部元素偏向一侧 | 锁住目标宽度，按地图净高收紧画布高度或外边距。给底部色条和图例用同高基线或独立槽，平衡两侧余量 |
| 文件过大、栅格模糊或页宽变化 | 密集图层用 `rasterized=True`，按目标调 DPI，用 `figsize` 固定成品宽高并复核导出参数 |
| 图层平移、镜像或局部框连错 | 回到源 CRS、目标 CRS 和栅格 transform，按地标核验坐标方向和 inset 覆盖 |
