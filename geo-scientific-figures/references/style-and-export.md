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

## 套图级整体风格与布局一致性规划

同画布组合图、同批次或同章节的系列单图均先确定共用规格，再编码。以一张代表图确定样式和布局，将规格应用到其余单图和同用途面板。组合图中的地图与统计轴各用相应的坐标样式。

| 维度 | 套图共用规格 |
| --- | --- |
| 画幅与空间布局 | 同研究区系列单图锁定投影、`extent`、经纬刻度步长、网格密度与线型、成品宽高和外边距比例。共用同一套刻度定位规则，避免各图随数据重新定范围 |
| 字体、线宽与标注 | 固定标题命名格式和字体层级，统一刻度精度、单位写法、边框与网格线宽。所有子图编号采用同一字号和锚点 |
| 配色与色条 | 按物理意义及比较关系选择顺序或发散配色，结合有效值域和主体分位数定范围。对应色条统一方向、厚度、离图间距、刻度样式和端形。同一物理量且比较口径一致时才共享色标 |
| 辅助元素 | 统一 NoData 口径和图例样式，固定比例尺、指北针和 `add_stats_box()` 的启用规则及角落位置。物理约束或关键数据遮挡确需例外时，记录原因及涉及的图件 |

- **色系示例。** 物理属性相近的同向变量采用亮度走向和饱和度协调的色系，例如 `YlGn` 搭配 `BuGn`、`YlGnBu` 或 `Greens`。清淡系列避免突然加入深紫至亮黄的高反差色系。把主体数值区间放在一起比较，检查缺包回退后的实际颜色，确保相邻不同变量可辨。共享色标时统一归一化和刻度。
- **色条端形示例。** 稍放宽整洁端点能覆盖有效极值且保留主体对比度时，优先全套 `extend="neither"`。确需截尾则先判断可比面板能否采用同一口径。对称发散色条任一端截断即用双尖 `"both"`，顺序色条按实际截断端设置，例如只截高值用 `"max"`。保留混合端形时，核对色条基线与含尖端的总长，并在交付说明中记录截尾阈值、方向和原因。

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
- 分类颜色同时依靠明暗、轮廓、纹理或线型增强区分。黑白图以 hatch 和黑色描边区分柱或地类，交稿前查看灰度版。

- 发散变量先按物理含义确定中心。需要同等强调正负同幅变化时用对称范围。

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

## 随图脚本与可调参数

每次出图都把完整可重跑的 Python 脚本和最终图件保存在同一目录。单图可命名为 `plot_fig_name.py`，同一批图可共用 `plot_*.py`。脚本从约定的输入文件读数据并导出成品。把输入和工具箱指向项目中可访问的位置，跨机交付时可随项目提供工具箱。禁止仅存临时脚本或运行后删除。交付前在图件目录用新进程运行 `python plot_xxx.py` 验证。

系列单图和组合图优先共用一份顶部基础样式与布局常量。批次脚本逐条读取配置，变量字典只记录输入路径、数据键、输出名、标题、色表或范围等实际差异。组合图从同一配置生成各面板，系列单图则用同一绘图入口逐文件导出。

模板演示 `plot_fields.py`。`fields.npz` 存放已核验的局部等面积投影网格，包含同形状的 `cover`、`moisture` 二维数组和米制 `extent=(左, 右, 下, 上)`。示例用 `NaN` 标记外部背景。按实际项目调整顶部五块带中文注释的参数，绘图段始终读取这些配置。

```python
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.ticker import MultipleLocator

# 1. 路径与输出
OUT_DIR = Path(__file__).resolve().parent  # 图件与本脚本同目录
INPUT = OUT_DIR / "fields.npz"  # 改为项目数据的位置
KIT_DIR = OUT_DIR  # geo_fig_kit.py 所在目录，也可指向本机 Skill 的 scripts 目录
OUT_NAME = "fields"
FORMATS, DPI, PREVIEW_DPI = ("png", "pdf"), 300, 180

# 2. 画布与排版
PRESET, FIGSIZE = "journal-en", (7.2, 3.2)  # 宽、高均为英寸，按网格比例复核净高
MARGINS = dict(left=0.09, right=0.97, bottom=0.20, top=0.85)
PANEL_GAPS = dict(wspace=0.34, hspace=0.22)
CBAR_ORIENTATION, CBAR_SIZE, CBAR_PAD = "horizontal", "4%", 0.46  # 厚度、间距
X_LABEL, Y_LABEL = "Easting (m)", "Northing (m)"  # 按投影坐标单位修改
X_STEP, Y_STEP = 200, 100  # 同网格地图共用刻度步长，单位 m

# 3. 字号与线宽
TITLE_PT, AX_TICK_PT, CBAR_TICK_PT, PANEL_PT, STATS_PT = 9, 7, 7, 9, 7
FRAME_LW, GRID_LW, GRID_COLOR, GRID_LINESTYLE = 0.7, 0.35, "0.87", "-"  # 线宽单位 pt
PANEL_LOC = "upper left"  # 子图编号的统一锚点

# 4. 变量配色与色标
# 同向的相关变量可在 YlGn、BuGn、YlGnBu、Greens 中选协调且可辨的搭配。
# neither 为平端。对称发散变量确需截尾时用 both，顺序变量只截高端用 max。
SCALE_DEFAULTS = dict(unit="Fraction", vmin=0.0, vmax=1.0, vcenter=None,
                      ticks=(0, 0.5, 1), extend="neither", nodata="none")
VARIABLES = {
    "cover": dict(title="Vegetation cover", cmap="YlGn"),
    "moisture": dict(title="Surface moisture", cmap="BuGn"),
}

# 5. 可选要素开关
SHOW_SUPTITLE, SUPTITLE = False, "Surface conditions"
SHOW_STATS, STATS_LOC = False, "upper left"  # 统计框只放在确认有空白的角落


def main():
    sys.path.insert(0, str(KIT_DIR))
    from geo_fig_kit import (add_aligned_colorbar, add_panel_label, add_stats_box,
                             apply_preset, get_cmap_safe, save_figure, style_map_ax)

    with mpl.rc_context(), np.load(INPUT) as data:
        apply_preset(PRESET)
        fig, axes = plt.subplots(1, len(VARIABLES), figsize=FIGSIZE, squeeze=False)
        fig.subplots_adjust(**MARGINS, **PANEL_GAPS)
        for index, (ax, (key, overrides)) in enumerate(zip(axes.flat, VARIABLES.items())):
            cfg = SCALE_DEFAULTS | overrides
            field = np.ma.masked_invalid(data[key])
            palette = get_cmap_safe(cfg["cmap"]).with_extremes(bad=cfg["nodata"])
            limits = dict(vmin=cfg["vmin"], vmax=cfg["vmax"])
            norm = Normalize(**limits) if cfg["vcenter"] is None else TwoSlopeNorm(vcenter=cfg["vcenter"], **limits)
            image = ax.imshow(field, extent=data["extent"], origin="upper", aspect="equal",
                              cmap=palette, norm=norm, rasterized=True)
            style_map_ax(ax, linewidth=FRAME_LW)
            ax.set_title(cfg["title"], fontsize=TITLE_PT)
            ax.set_xlabel(X_LABEL, fontsize=AX_TICK_PT)
            if index == 0:
                ax.set_ylabel(Y_LABEL, fontsize=AX_TICK_PT)
            ax.xaxis.set_major_locator(MultipleLocator(X_STEP))
            ax.yaxis.set_major_locator(MultipleLocator(Y_STEP))
            ax.tick_params(labelsize=AX_TICK_PT)
            ax.grid(color=GRID_COLOR, linewidth=GRID_LW, linestyle=GRID_LINESTYLE)
            add_panel_label(ax, chr(ord("a") + index), loc=PANEL_LOC, fontsize=PANEL_PT)

            cbar = add_aligned_colorbar(fig, image, ax, orientation=CBAR_ORIENTATION,
                                         size=CBAR_SIZE, pad=CBAR_PAD, label=cfg["unit"], extend=cfg["extend"])
            cbar.set_ticks(cfg["ticks"])
            cbar.ax.tick_params(labelsize=CBAR_TICK_PT)
            cbar.outline.set_linewidth(FRAME_LW)
            if SHOW_STATS and field.count():
                add_stats_box(ax, f"Mean: {field.mean():.3f}", loc=STATS_LOC, fontsize=STATS_PT)

        if SHOW_SUPTITLE:
            fig.suptitle(SUPTITLE, fontsize=TITLE_PT)
        save_figure(fig, OUT_DIR / OUT_NAME, FORMATS, dpi=DPI, preview_dpi=PREVIEW_DPI)
        plt.close(fig)


if __name__ == "__main__":
    main()
```
