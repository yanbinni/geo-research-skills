# 版式、配色与文件导出

## 尺寸与字号

尺寸均为成品尺寸。正文插入、期刊排版和幻灯片摆放按该宽度设置。`figsize` 单位为英寸，1 in = 25.4 mm，线宽和字体用 pt。下表采用 `apply_preset()` 和 `PRESETS` 的默认值。

| 参数 | `journal-en` | `thesis-cn` | `slides` | `custom` |
| --- | --- | --- | --- | --- |
| `single` | 3.50 in / 88.90 mm | 3.00 in / 76.20 mm | 6.50×4.00 in / 165.10×101.60 mm | 用户指定 |
| `one-and-half` | 5.20 in / 132.08 mm | — | — | 用户指定 |
| `double` | 7.20 in / 182.88 mm | 5.80 in / 147.32 mm | 10.00×5.50 in / 254.00×139.70 mm | 用户指定 |
| 画布高度 | 地图按比例与边距反推 | 地图按比例与边距反推 | 按目标宽高 | 用户指定 |
| 基础 / 标题 / 轴标签 | 8 / 9 / 8 pt | 9 / 10 / 9 pt | 12 / 14 / 12 pt | 用户指定 |
| 刻度 / 图例 / 子图编号 | 7 / 7 / 9 pt | 8 / 8 / 10 pt | 11 / 11 / 14 pt | 用户指定 |
| 外框与主刻度 | 0.70 pt | 0.75 pt | 1.00 pt | 用户指定 |
| 主数据线 | 1.40 pt | 1.40 pt | 1.20 pt | 用户指定 |
| 统计柱描边 | 默认 0.60 pt | 默认 0.60 pt | 建议 1.00 pt | 用户指定 |
| 辅助网格 | 0.45 pt，浅灰 | 0.45 pt，浅灰 | 建议 0.6 pt，浅灰 | 按背景和介质 |
| 成品位图 / 预览 | 300 / 180 DPI | 300 / 180 DPI | 300 / 180 DPI | 以交付要求为准 |

- 用 `PRESETS[preset]["linewidth"]` 显式给地图、统计和色条边框赋值。`make_trend()`、`make_grouped_bar()` 的专用线宽可用参数覆盖。
- 锁成品宽度，不锁死高度。从目标栏宽分配各面板绘图区及色条、刻度、间距，再按地图实际显示的宽高比例计算绘图区高度并加上最小必要外边距。同排有多幅图时以需要的绘图区净高和底部元素共同定高。`aspect=0.62` 是一般图的初始值，地图按推算的 `height / width` 设置 `aspect` 或直接用 `figsize=(width, height)`。不拉伸地理比例或用白边填满高瘦、扁平图幅。
- 自定义尺寸可在 `rc_context()` 内应用邻近预设，随后覆盖 `rcParams` 和 `figsize`。期刊要求优先于本表。编号字号可由 `add_panel_label(..., fontsize=...)` 精确指定。
- 区分线的语义。外框和分隔线弱于主体数据，显著性符号保持细密但可见。不依赖把大画布缩小来控制字号。

## 中英混排与跨机检查

| 平台 | 建议回退顺序 |
| --- | --- |
| Windows | Arial → Microsoft YaHei → SimHei / SimSun → DejaVu Sans |
| Linux | Arial（若存在）→ Noto Sans CJK SC / Source Han Sans SC → WenQuanYi Micro Hei → DejaVu Sans |
| macOS | Helvetica → PingFang SC / Songti SC → Noto Sans CJK SC → DejaVu Sans |

- `doctor` 显示当前 Python 实际识别的字体家族。首次制图用目标标题、刻度、单位和上下标渲染样张，检查 Matplotlib 的 `Glyph missing` 警告。
- `apply_preset("thesis-cn", font_override=("Times New Roman", "SimSun"))` 可适配指定的论文样式。英文与数字受专业规范约束时，用字库覆盖验证过的顺序。需要强制单个标签用宋体时，为该文本指定 `FontProperties(family=...)`。
- 字体刚安装或当前环境无法发现时，可用 `font_manager.fontManager.addfont(path)` 在本次进程注册有使用许可的本地字体，再应用预设。SVG 保留文字后，接收电脑也需具备相应字库。
- 正常坐标轴保持 `axes.unicode_minus=False` 可避免某些中文字体的 U+2212 显示方块。手写 Unicode 负号、希腊字母、度符号、乘号和数学公式仍须检查实际字形。

## 色表按变量语义选取

| 数据 | 优先色表 | Matplotlib 回退 | 使用条件 |
| --- | --- | --- | --- |
| 植被 NDVI、覆盖度和 GPP | `algae` / `batlow` | `algae` → `YlGn`，`batlow` → `viridis` | 量级有序时用顺序色表，正负距平用发散色表 |
| 水深、降水和水分 | `deep` / `rain` / `haline` | `deep` / `rain` → `YlGnBu`，`haline` → `cividis` | 核对深浅方向。也可直接用 `Blues`、`BuGn` 或 `PuBuGn` |
| LST、温度场 | `thermal` / `lajolla` | 两者均 → `YlOrRd` | 绝对温度用顺序色表，如 `YlOrRd` 或 `OrRd`，注明 ℃ 或 K |
| DEM、高程 | `davos` / `oleron` / `oslo` | 三者均 → `cividis` | `oleron` 有海陆分段语义，先核对分界。纯陆域优先 `davos` |
| 其他有序强度 | `matter` | `magma` | 纯植被强度也可选 `Greens`，按实际亮度梯度确认对比度 |
| 净碳交换、变化、异常和像元趋势 | `vik` / `broc` / `cork` / `balance` / `delta` | `vik` → `RdBu_r`，`broc` / `cork` → `BrBG`，`balance` / `delta` → `coolwarm` | `TwoSlopeNorm` 对齐物理零点或参考值。也可直接选 `PuOr`、`PRGn`、`PiYG` 或 `RdYlBu`，核对正负方向和印刷可读性 |
| LULC | 语义 `ListedColormap` | 同语义独立色块 | 森林绿、农田黄、水域蓝、建成区砖红等；见遥感参考 |
| 离散统计比较 | `SCI_PALETTE` | 同一套固定色值 | 深蓝、青绿、砖红、琥珀、紫灰、中性灰；组间含义跨图固定 |

`get_cmap_safe()` 的内置 ColorBrewer 顺序色表包括 `YlGn`、`YlGnBu`、`YlOrRd`、`Blues`、`Greens`、`BuGn`、`OrRd`、`PuBuGn`，发散色表包括 `RdBu`、`BrBG`、`PuOr`、`PRGn`、`PiYG`、`RdYlBu`。名称大小写均可，后缀 `_r` 表示反转。回退保留顺序或发散性质，核对实际色表、正负含义及亮度梯度。[Matplotlib 内置色表](https://matplotlib.org/stable/gallery/color/colormap_reference.html) · [Scientific colour maps](https://www.fabiocrameri.ch/colourmaps/)

- 禁用 `jet`、`rainbow`、`hsv` 及其反转版本。按色表的亮度梯度、物理含义和色觉缺陷预览挑选。
- 同图中不共享色标的不同物理变量，相邻面板禁止使用同一色表。核对缺包回退后的实际颜色，避免两个名称映射到同一套颜色。南京生产力组合图可用 GPP `YlGn`、NPP `viridis` 或 `cividis`、NEP `RdBu_r` 或 `BrBG`。
- 发散颜色先确定中心再取范围。需要用同等饱和度比较正负同幅变化时用对称范围，共对照的图统一上下限。
- 对称发散色条禁止一端尖、一端平。只要任一端截断，使用 `extend="both"` 并在图注注明实际截断侧。若能用整洁的对称端点覆盖全值，使用 `extend="neither"`。并排图的色条方向、端部形态和位置应协调。
- 分类颜色同时依靠明暗、轮廓、纹理或线型增强区分。黑白图以 hatch 和黑色描边区分柱或地类，交稿前查看灰度版。

## NoData 分级

| 掩膜类型 | 图面 | 说明位置 |
| --- | --- | --- |
| 研究区外纯背景 | 纯白或透明，保留有效零值的正常色标颜色 | 省略 NoData 图例 |
| 连续图有显著内部缺测或水域 | 中性浅灰，与零值和外部背景可区分 | 图注说明。默认禁止底部单挂 NoData 框。用户明确要求图内说明时，紧凑放在主图空角 |
| 离散分类图有内部无数据 | 用独立的中性色块或纹理 | 收入已有分类图例盒末项 |

先用研究区边界区分外部背景与内部掩膜。两类共存时，可把 `bad` 设为透明，在有效图层下单独画一层内部浅灰掩膜。检查透明区叠到最终背景后的显示效果。

## 预览与目标格式

| 场景 | 常用交付 | 核查项目 |
| --- | --- | --- |
| 印刷或投稿 | PDF 主文件；按稿约补 TIFF 300–600 DPI | 页尺寸、字体嵌入、图层体积、DPI；色彩模式依据刊方要求 |
| Word 论文和大创 | 高 DPI PNG；需要 Windows 矢量并确认接收端支持时可用 EMF | 文档插入后锁定纵横比与成品宽度，检查 Office 压缩和字体 |
| 答辩与组会 | 高 DPI PNG 或目标软件支持的 SVG | 现场显示比例、深浅背景对比、最细线与最小字 |
| 后期编辑 | PDF 或 SVG，附绘图代码 | PDF 字体和 SVG 文字元素、跨机字体；编辑器实测出图 |

- 给大栅格、密集散点和密集显著性点设置 `rasterized=True`，边界、刻度、线和文字保留原 artist。设置 `pdf.fonttype=42`、`ps.fonttype=42`、`svg.fonttype='none'`。
- `save_figure(fig, "out/panel", ("png", "pdf", "svg"), dpi=300, preview_dpi=180)` 输出成品与 `panel.preview.png`，打印绝对路径、PNG 像素、文件大小。超过 15 MB 的矢量文件会提示检查密集图层。
- `save_figure()` 始终保留 `figsize`。`tight=True` 根据 `pad_inches` 检查裁切风险，也提示任一方向的内容占比低于 78% 且该方向最长外边距超过 0.45 in 的白边。固定目标宽度后调整高度或子图外边距，再渲染复核。用 `GridSpec`、`subplots_adjust()` 或合适的布局引擎给外置文字留空间，避免 `bbox_inches="tight"` 改写成品宽高。
- TIFF 的分辨率可由 `formats=("tiff",)` 与 `dpi=600` 指定。EMF 需用能保留矢量并支持 EMF 的外部转换流程，检查字体、透明度和线宽。Matplotlib 工具箱按当前后端支持的格式保存。
- 位图宽高约等于英寸宽高乘 DPI，允许整数取整差异。PDF 的页面宽度以 pt 计，除以 72 得到英寸。SVG 用 `<svg>` 的 `width`、`height` 和 `viewBox` 检查画板与内容。
