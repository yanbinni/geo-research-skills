---
name: geo-scientific-figures
description: >-
  用 Python / Matplotlib 制作地理、遥感、地球科学出版级静态图。适用于遥感影像图、地理专题图、
  研究区概况图、精度验证散点图、分组柱状图、趋势图、混淆矩阵和地图＋统计组合图，
  用于毕业论文、大创报告、SCI 投稿和答辩汇报。
  Publication-ready remote-sensing imagery, thematic maps, study-area maps, validation scatterplots,
  grouped bars, trends, confusion matrices, and map–statistics composites for theses, reports,
  journals, and slides. 不用于交互式 Web 地图、Plotly/Bokeh 仪表盘、纯 3D 建模或 Figma 信息图。
  Excludes interactive web maps, Plotly/Bokeh dashboards, 3D modeling, and Figma infographics.
---

# 地学科研制图

按投放场景确定真实物理尺寸，按面板用途选取样式，在同一份图中统一字号、标注、单位和间距。

## 适用范围

- ✅ 静态栅格或矢量专题地图、研究区概况、定位小图、局部放大图。
- ✅ 真彩色和假彩色合成、土地覆被、DEM、距平、变化检测及像元趋势图。
- ✅ 反演精度验证、分组柱状图、趋势与不确定性、混淆矩阵和其他统计图。
- ✅ 地图与统计组合、对照图、毕业论文、大创、英文论文及组会答辩出图。
- ❌ 交互式 Web 地图、Plotly/Bokeh 仪表盘、纯探索性临时图。
- ❌ 纯 3D 建模、Figma 主导的信息图。

## 物理版式速查

| 预设 | 成品宽度或宽×高 | 字号 | 边框 / 线宽 | 字体 |
| --- | --- | --- | --- | --- |
| `journal-en`（默认） | 单栏 3.5 in（89 mm）、1.5 栏 5.2 in（132 mm）、双栏 7.2 in（183 mm） | 7–9 pt | 0.7 pt | Arial → Helvetica → DejaVu Sans |
| `thesis-cn` | 半幅 3.0 in（76 mm）、通栏 5.8 in（约 14.8 cm Word A4 版心） | 8–10 pt | 0.75 pt | 中英混排回退，`axes.unicode_minus=False` |
| `slides` | 6.5×4.0 in 或 10.0×5.5 in | 11–14 pt | 边框 1.0 pt、数据线 1.2 pt | 中英混排，高对比 |
| `custom` | 严格采用用户指定的尺寸、版式或期刊规范 | 随目标 | 随目标 | 随目标 |

`apply_preset()` 的 `single` 对应单栏、半幅或小尺寸 PPT，`double` 对应双栏、通栏或大尺寸 PPT。
`one-and-half` 仅供 `journal-en` 使用。论文和报告**锁成品宽度，不锁死高度**。PPT 采用表中目标画幅，用户指定的成品尺寸优先。
`custom` 是版式路径。使用最接近的预设初始化，再明确覆盖字体、线宽、宽高和交付 DPI。

- 以 1:1 成品尺寸设计。地图先从目标栏宽扣除刻度、色条和面板间距，再用实际投影后的地理纵横比反推绘图区高度，最后加上必需的上下边距。高瘦或扁平研究区都禁止套用固定 `aspect=0.62` 后以大片白边填缝。
- 空间不足时调整面板结构、标签密度或图例槽。编号默认用同一字号、同一位置的粗体 `(a)`、`(b)`、`(c)`。
- 删除无信息装饰，使用克制留白。优先将图例放入独立空位或框外槽，始终避开数据。
- 使用 `matplotlib.rc_context()` 约束样式作用域。禁止在全局 `rcParams` 中编码 `axes.spines.top/right` 的关闭状态。

## 面板路由

1. 面板是否展示真实空间位置、覆盖范围或地形？
   - 是 → 地图。调用 `style_map_ax()`，再根据投影设置经纬标注、网格或米制坐标，并设置显示范围。
   - 遥感栅格或气候变量额外核对方向、NoData、色标和网格定义。
2. 面板是否展示分布、时间序列、指标比较或预测验证？
   - 是 → 统计图。调用 `style_stat_ax()`；有需要时只在用于读数的方向开淡色网格。
3. 图中同时有地图和统计图？
   - 逐面板分别应用样式，共用字体、编号锚点、视觉层级和间距。为色条和图例预留空间。

同一份 GeoTIFF、NetCDF 或 Shapefile 可以走不同路径。真实空间分布走地图，区域均值时序或分布对比走统计图。
同一要素跨面板保持相同语义色。例如主图显示 NDVI 距平，同排统计图显示面积加权区域均值和验证结果。

| 输入 | 空间任务 | 统计任务 |
| --- | --- | --- |
| GeoTIFF 多波段影像 | RGB 合成或土地覆被专题图 | 分区域比较地类面积占比 |
| NetCDF 气候数据 | 降水距平或像元趋势地图 | 区域月平均与不确定性带 |
| Shapefile / GPKG 样区 | 采样点分布与研究区定位 | 按站点或地类比较数值分布 |

若要表示空间观测密度，用空间网格聚合；若要表示观测与预测的配对密度，用统计坐标分箱。
分析阶段使用原始或经过科学验证的网格；预览降采样服务于显示和体检。

## 八条红线

1. 出图前用 `geo_fig_kit.py inspect` 探测真实的空间数据。核对 CRS、范围、NoData、方向和分位数，再写绘图参数。表格等其他来源先核对字段、单位和值域。
2. 地图必须使用封闭外框，显式对齐图层 CRS 和视图范围。统计图默认去顶右框，保留左底轴。
3. 涉及中国全图或中国国界线时，仅使用用户提供的合规标准审图矢量。严禁默认使用 Cartopy 的 Natural Earth 国界、南海九段线或争议边界。缺底图时暂停地图部分，说明审图风险并索要合规图层。
4. NoData 分级显示，并与有效 `0` 区分。研究区外的背景掩膜用纯白或透明，省略其 NoData 图例。连续色标图有显著的内部缺测或水域掩膜时，用中性浅灰并在图注说明，默认禁止在画布底部单挂 NoData 图例框。仅用户明确要求图内标出时，在主图空角紧凑注明。只有离散分类图将内部 NoData 收入已有图例盒末项。
5. 连续与发散图使用感知均匀、色觉缺陷友好的色表。严禁 `jet`、`rainbow`、`hsv`。变化、异常和趋势以 `0` 或定义好的参考值对齐中性色。
6. 比例尺、指北针必须符合 CRS 和地图跨度。大跨度 EPSG:4326 禁放单一线性比例尺。经线弯曲或网格北偏转时，按局部真北计算方向，或省略指北针。
7. 矢量 PDF/SVG 中的大栅格和密集散点设置 `rasterized=True`。保持文字和关键线条可编辑，使用 `pdf.fonttype=42` 及 `svg.fonttype='none'`。
8. 必须打开渲染预览做 Visual QA。检查目标格式内的文字、边界、色标、画布尺寸和文件体积，修复后重验。

## 四步工作流

### 1. 环境与数据体检

在 Skill 目录下执行以下命令，路径含空格时加引号。

```bash
python scripts/geo_fig_kit.py doctor
python scripts/geo_fig_kit.py inspect "data/scene.tif"
python scripts/geo_fig_kit.py inspect "data/study_area.gpkg" --layer study_area
python scripts/geo_fig_kit.py inspect "data/climate.nc"
```

- 首次换机先运行 `doctor`，确认当前 Python、字体、核心依赖与所需可选包。
- `inspect` 对支持的真实输入逐份运行。命令返回 0 表示完成，1 表示数据或环境错误，2 表示命令参数错误，3 表示数据操作缺依赖或依赖无法加载。
- 分位数来自输出标注的全像元或抽样估计。稀有类、极值和显示范围临界时，用原始分辨率局部窗口复核。
- `CRS: 缺失` 时向数据提供者查证。未知 CRS、轴序和数值单位会影响投影与结果，须在编码前解决。

### 2. 定型确认

- 从交付场景推导预设。版式、目标场景或所需合规底图无法从请求推定时，只问影响成品的最少信息。
- 用户已提供模板或目标期刊时，确认成品尺寸、最小字号、允许格式、DPI 和是否需要分面交付。
- 地图先定范围、源 CRS、目标 CRS、底图来源和色标口径。统计先定比较单位、聚合方法和误差定义。
- 并列对照先确认是否允许共用色标或 y 轴。用于同量纲对比时统一刻度和归一化。

### 3. 编码出图

- 把 `scripts/` 加入绘图脚本的模块搜索路径，复用 [geo_fig_kit.py](scripts/geo_fig_kit.py)。预设在创建画布和坐标轴前应用。
- 给地图或统计轴显式传入所选预设的边框宽度。经纬度标签由明确定义的坐标系驱动。
- 选择色表后再确定 `norm`、坏值色和单位。分类使用离散图例，可加纹理和黑色描边用于灰度印刷。
- 输出独立预览 PNG 和目标格式。对 PDF/SVG 在 artist 层决定栅格化，保护文字和矢量线。

```python
import matplotlib as mpl
import matplotlib.pyplot as plt
from geo_fig_kit import PRESETS, add_panel_label, apply_preset, save_figure, style_stat_ax

preset = "thesis-cn"
with mpl.rc_context():
    size = apply_preset(preset, "single")
    fig, ax = plt.subplots(figsize=size, layout="constrained")
    style_stat_ax(ax, linewidth=PRESETS[preset]["linewidth"], grid_axis="y")
    ax.plot([1, 2, 3], [0.31, 0.42, 0.39], marker="o")
    ax.set(xlabel="月份", ylabel="NDVI")
    add_panel_label(ax, "a")
    save_figure(fig, "out/ndvi", ("png", "pdf"))
    plt.close(fig)
```

### 4. 视觉与文件验收

- 打开预览，按 [复合图与验收](references/composite-and-qa.md) 完成 8 项视觉检查。修复重叠、截断、过曝、边界错位和符号歧义后重新渲染。
- 在最终目标宽度检查字、线和图例。核对 PDF 页面或 SVG 画板物理尺寸，并按交付 DPI 检查位图像素。
- 交付图与绘图代码时列明预设、实际版式、数据抽样、关键制图假设，以及产生了实质影响的降级。

## 按需加载

只打开当前面板或交付步骤所需的文档，避免一次性预加载全部参考。

| 文件 | 何时打开 |
| --- | --- |
| [版式与导出](references/style-and-export.md) | 确定宽高、字号、字体回退、科学色表与文件格式 |
| [地图制图](references/cartography-core.md) | 选择投影、经纬网、审图底图、比例尺、定位或放大图 |
| [遥感图](references/remote-sensing.md) | 读取栅格、影像合成、LULC、变化与显著性、DEM 或 NetCDF |
| [地学统计图](references/geo-statistics.md) | 精度验证、分组柱状图、趋势和不确定性、热力图、混淆矩阵与分布对比 |
| [复合图与验收](references/composite-and-qa.md) | 排列混合面板、对齐共享图例与色条、核查预览和最终文件 |
| [Python 工具箱](scripts/geo_fig_kit.py) | 运行 CLI，或复用读图、取色、统计、布局和导出函数 |

## 可选依赖的降级路径

- 核心制图只直接依赖 NumPy 和 Matplotlib。可选库在相应操作中加载。
- 缺 Cartopy 时，已知经纬度数据可用 Matplotlib 普通轴和 `format_lonlat_ticks()`。要叠加矢量时用可用的 GeoPandas 读入并重投影。复杂投影需要等效变换或相应依赖。
- 缺 Rasterio、GeoPandas 或 xarray 时，CLI 返回安装建议。可使用经核验并携带空间元数据的预转换数组或几何；源数据转换和体检仍需适当工具。
- 缺 cmcrameri/cmocean 时，按变量语义回退至 Matplotlib 色表。共用色标的图组保持同一色表和 `norm`，不同物理变量的邻接面板须使用不同实际色表。
- 缺 SciPy 时，验证图仍可用 NumPy OLS、二维分箱与 Matplotlib `hexbin`。缺 rioxarray 时可保留 xarray 分析与 Rasterio 重投影流程。
- 缺 matplotlib-scalebar 时，可在单位已核实的投影坐标下手动画尺度线；不能验证物理距离时省略该要素。
