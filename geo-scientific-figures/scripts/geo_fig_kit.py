"""面向地理、遥感与地球科学的 Matplotlib 制图工具与数据体检 CLI。"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import math
import platform
import struct
import sys
import warnings
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.cm import ScalarMappable
    from matplotlib.colorbar import Colorbar
    from matplotlib.colors import Colormap
    from matplotlib.container import BarContainer
    from matplotlib.figure import Figure
    from matplotlib.image import AxesImage
    from matplotlib.lines import Line2D
    from matplotlib.offsetbox import AnchoredText
    from matplotlib.text import Annotation
    from matplotlib.transforms import Bbox
    from numpy.typing import ArrayLike, NDArray
    from rasterio.crs import CRS
    from xarray import DataArray


PRESETS: dict[str, dict[str, Any]] = {
    "journal-en": {
        "widths": {"single": 3.5, "one-and-half": 5.2, "double": 7.2},
        "heights": {},
        "fonts": ("Arial", "Helvetica", "DejaVu Sans"),
        "sizes": {"base": 8, "title": 9, "label": 8, "tick": 7, "legend": 7, "panel": 9},
        "linewidth": 0.7, "data_linewidth": 1.4, "dpi": 300, "preview_dpi": 180,
    },
    "thesis-cn": {
        "widths": {"single": 3.0, "double": 5.8},
        "heights": {},
        "fonts": (
            "Arial", "Helvetica", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC",
            "Source Han Sans SC", "SimHei", "SimSun", "WenQuanYi Micro Hei", "DejaVu Sans",
        ),
        "sizes": {"base": 9, "title": 10, "label": 9, "tick": 8, "legend": 8, "panel": 10},
        "linewidth": 0.75, "data_linewidth": 1.4, "dpi": 300, "preview_dpi": 180,
    },
    "slides": {
        "widths": {"single": 6.5, "double": 10.0},
        "heights": {"single": 4.0, "double": 5.5},
        "fonts": (
            "Arial", "Helvetica", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC",
            "Source Han Sans SC", "SimHei", "SimSun", "WenQuanYi Micro Hei", "DejaVu Sans",
        ),
        "sizes": {"base": 12, "title": 14, "label": 12, "tick": 11, "legend": 11, "panel": 14},
        "linewidth": 1.0, "data_linewidth": 1.2, "dpi": 300, "preview_dpi": 180,
    },
}

SCI_PALETTE: dict[str, str] = {
    "blue": "#175181",
    "teal": "#00857D",
    "brick": "#AE4938",
    "amber": "#D39928",
    "purple_gray": "#75628F",
    "gray": "#686F76",
}

_CMAPS: dict[str, tuple[str, str]] = {
    "batlow": ("cmcrameri", "viridis"), "lajolla": ("cmcrameri", "YlOrRd"),
    "oslo": ("cmcrameri", "cividis"), "davos": ("cmcrameri", "cividis"),
    "oleron": ("cmcrameri", "cividis"), "vik": ("cmcrameri", "RdBu_r"),
    "broc": ("cmcrameri", "BrBG"), "cork": ("cmcrameri", "BrBG"),
    "thermal": ("cmocean", "YlOrRd"), "haline": ("cmocean", "cividis"),
    "deep": ("cmocean", "YlGnBu"), "rain": ("cmocean", "YlGnBu"),
    "algae": ("cmocean", "YlGn"), "matter": ("cmocean", "magma"),
    "balance": ("cmocean", "coolwarm"), "delta": ("cmocean", "coolwarm"),
}
_BUILTIN_SEQUENTIAL = (
    "viridis", "cividis", "plasma", "inferno", "magma",
    "YlGn", "YlGnBu", "YlOrRd", "Blues", "Greens", "BuGn", "OrRd", "PuBuGn",
)
_BUILTIN_DIVERGING = ("coolwarm", "RdBu", "BrBG", "PuOr", "PRGn", "PiYG", "RdYlBu")
_BUILTIN_CMAPS = {name.casefold(): name for name in (*_BUILTIN_SEQUENTIAL, *_BUILTIN_DIVERGING)}
_DIVERGING = {name.casefold() for name in _BUILTIN_DIVERGING} | {"vik", "broc", "cork", "balance", "delta"}
_BANNED = {"jet", "rainbow", "hsv", "gist_rainbow"}
_OPTIONAL = {
    "rasterio": "rasterio", "geopandas": "geopandas", "cartopy": "cartopy",
    "xarray": "xarray", "rioxarray": "rioxarray", "scipy": "scipy",
    "cmcrameri": "cmcrameri", "cmocean": "cmocean", "matplotlib_scalebar": "matplotlib-scalebar",
}
_FONT_PROBES = (
    "Arial", "Helvetica", "DejaVu Sans", "Times New Roman", "SimSun", "Microsoft YaHei",
    "SimHei", "Noto Sans CJK SC", "Noto Sans CJK TC", "Source Han Sans SC", "PingFang SC",
    "Songti SC", "WenQuanYi Micro Hei",
)
_RASTER_EXTS = {".tif", ".tiff", ".img", ".vrt"}
_VECTOR_EXTS = {".shp", ".geojson", ".gpkg", ".fgb"}
_NETCDF_EXTS = {".nc", ".nc4"}
_RASTER_SAMPLE_SIDE = 1024
_NC_SAMPLE_LIMIT = 250_000


class _DependencyError(RuntimeError):
    """记录当前数据操作缺少的运行依赖。"""


def _require(module: str, install: str | None = None) -> ModuleType:
    """按需导入依赖，并给出当前解释器的安装命令。"""
    try:
        return importlib.import_module(module)
    except Exception as exc:
        package = install or module
        raise _DependencyError(
            f"无法加载 {module}（{exc}）。请检查当前环境或运行 python -m pip install {package}"
        ) from exc


def _available_fonts() -> dict[str, str]:
    """返回 Matplotlib 能实际找到的字体家族名。"""
    from matplotlib.font_manager import fontManager

    return {font.name.casefold(): font.name for font in fontManager.ttflist}


def apply_preset(
    preset: str = "journal-en", layout: str = "double", aspect: float = 0.62,
    font_override: str | Sequence[str] | None = None,
) -> tuple[float, float]:
    """应用字体、线宽和导出预设，返回画布英寸尺寸。PPT 使用固定宽高。"""
    import matplotlib as mpl

    if preset not in PRESETS:
        raise ValueError(f"未知预设 {preset!r}，可用值为 {', '.join(PRESETS)}。自定义版式请直接指定尺寸。")
    config = PRESETS[preset]
    if layout not in config["widths"]:
        raise ValueError(f"{preset} 可用版式为 {', '.join(config['widths'])}。")
    if not math.isfinite(aspect) or aspect <= 0:
        raise ValueError("aspect 必须为正的有限数。")

    available = _available_fonts()
    requested = (font_override,) if isinstance(font_override, str) else tuple(font_override or ())
    for family in requested:
        if family.casefold() not in available:
            warnings.warn(f"未找到指定字体 {family}，使用已安装的预设回退字体。", stacklevel=2)
    families = list(dict.fromkeys(
        available[name.casefold()] for name in (*requested, *config["fonts"])
        if name.casefold() in available
    )) or ["DejaVu Sans"]
    sizes = config["sizes"]
    mpl.rcParams.update({
        "font.family": families, "font.sans-serif": families,
        "font.size": sizes["base"], "axes.titlesize": sizes["title"],
        "axes.labelsize": sizes["label"], "xtick.labelsize": sizes["tick"],
        "ytick.labelsize": sizes["tick"], "legend.fontsize": sizes["legend"],
        "axes.linewidth": config["linewidth"], "lines.linewidth": config["data_linewidth"],
        "xtick.major.width": config["linewidth"], "ytick.major.width": config["linewidth"],
        "axes.unicode_minus": False, "legend.frameon": False,
        "axes.grid": False, "figure.dpi": config["preview_dpi"], "savefig.dpi": config["dpi"],
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    })
    width = config["widths"][layout]
    return width, config["heights"].get(layout, width * aspect)


def style_map_ax(ax: Axes, linewidth: float = 0.7, tick_length: float = 3.0) -> None:
    """闭合普通四边框或 GeoAxes 投影外框，统一底侧和左侧刻度。"""
    ax.set_axis_on()
    geo_spine = ax.spines.get("geo")
    for side in ("left", "right", "top", "bottom"):
        ax.spines[side].set_visible(geo_spine is None)
        ax.spines[side].set_linewidth(linewidth)
    if geo_spine is not None:
        geo_spine.set_visible(True)
        geo_spine.set_linewidth(linewidth)
    ax.tick_params(
        which="both", direction="out", length=tick_length, width=linewidth,
        bottom=True, left=True, top=False, right=False, labelbottom=True, labelleft=True,
        labeltop=False, labelright=False,
    )


def style_stat_ax(ax: Axes, linewidth: float = 0.7, grid_axis: str | None = None) -> None:
    """保留左、下坐标轴，可按 x、y 或 both 添加淡色引导线。"""
    if grid_axis not in (None, "x", "y", "both"):
        raise ValueError("grid_axis 应为 None、'x'、'y' 或 'both'。")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(linewidth)
    ax.tick_params(which="both", direction="out", top=False, right=False, width=linewidth)
    ax.grid(False, which="both")
    if grid_axis is not None:
        ax.set_axisbelow(True)
        ax.grid(True, axis=grid_axis, color="0.87", linewidth=0.45)


def add_panel_label(
    ax: Axes, label: str, loc: str = "upper left", fontsize: float | None = None,
    inside: bool = False,
) -> Annotation:
    """用固定点距标注括号式粗体编号，默认置于面板左上框外。"""
    import matplotlib as mpl

    locations = {"upper left": (0, 1), "upper right": (1, 1),
                 "lower left": (0, 0), "lower right": (1, 0)}
    if loc not in locations:
        raise ValueError(f"不支持的编号位置 {loc!r}。")
    x, y = locations[loc]
    text = label.strip().strip("()").strip()
    if not text:
        raise ValueError("子图编号不能为空。")
    above_anchor = (y == 1) != inside
    inset_x = (4 if x == 0 else -4) if inside else 0
    return ax.annotate(
        f"({text})", (x, y), xycoords="axes fraction", textcoords="offset points",
        xytext=(inset_x, 4 if above_anchor else -4),
        ha="left" if x == 0 else "right", va="bottom" if above_anchor else "top",
        fontsize=mpl.rcParams["axes.titlesize"] if fontsize is None else fontsize,
        fontweight="bold", annotation_clip=False, zorder=10,
    )


def add_stats_box(
    ax: Axes, lines: str | Sequence[str], loc: str = "upper left",
    fontsize: float | None = None, alpha: float = 0.82,
) -> AnchoredText:
    """按需在面板角落添加半透明圆角统计框，并返回可继续调整的对象。"""
    from matplotlib.offsetbox import AnchoredText

    text = lines if isinstance(lines, str) else "\n".join(lines)
    box = AnchoredText(text, loc=loc, prop={"size": "small" if fontsize is None else fontsize},
                       pad=0.3, frameon=True)
    box.patch.set(facecolor="white", edgecolor="0.65", linewidth=0.5, alpha=alpha)
    box.patch.set_boxstyle("round,pad=0,rounding_size=0.2")
    ax.add_artist(box)
    return box


def get_cmap_safe(name: str, fallback: str = "viridis") -> Colormap:
    """选用科学色表，缺可选库时使用匹配类型的 Matplotlib 色表。"""
    import matplotlib as mpl

    key = name.strip().casefold()
    base = key.removesuffix("_r")
    reverse = key.endswith("_r")
    if base in _BANNED:
        warnings.warn(f"禁用色表 {name!r}，改用安全色表。", stacklevel=2)
    elif base in _BUILTIN_CMAPS:
        return mpl.colormaps[_BUILTIN_CMAPS[base] + ("_r" if reverse else "")]
    elif base in _CMAPS:
        module, default = _CMAPS[base]
        try:
            cmap = getattr(_require(f"{module}.cm", module), base)
        except (_DependencyError, AttributeError):
            if reverse:
                default = default.removesuffix("_r") if default.endswith("_r") else f"{default}_r"
            return mpl.colormaps[default]
        return cmap.reversed() if reverse else cmap
    else:
        warnings.warn(f"色表 {name!r} 未收录，改用安全色表。", stacklevel=2)
    safe = fallback.strip().casefold()
    safe_base = safe.removesuffix("_r")
    if safe_base not in _CMAPS and safe_base not in _BUILTIN_CMAPS:
        safe = "viridis"
    return get_cmap_safe(safe)


def _reduced_shape(height: int, width: int, max_dim: int) -> tuple[int, int]:
    """按原长宽比计算有上限的输出像元数。"""
    scale = min(1.0, max_dim / max(height, width))
    return max(1, round(height * scale)), max(1, round(width * scale))


def read_raster_for_plot(
    path: str | Path, bands: int | Sequence[int] = 1, max_dim: int = 2000,
) -> tuple[np.ma.MaskedArray, tuple[float, float, float, float], CRS | None, bool]:
    """返回掩膜数组、extent、CRS 和旋转标志。多波段按 (H, W, C) 返回。"""
    import numpy as np

    rasterio = _require("rasterio")
    if max_dim < 1:
        raise ValueError("max_dim 至少为 1。")
    with rasterio.open(path) as src:
        single = isinstance(bands, (int, np.integer))
        indexes = [int(bands)] if single else list(bands)
        if not indexes or any(i not in src.indexes for i in indexes):
            raise ValueError(f"波段索引须来自 {src.indexes}。")
        height, width = _reduced_shape(src.height, src.width, max_dim)
        data = src.read(indexes, out_shape=(len(indexes), height, width), masked=True)
        data = np.ma.masked_invalid(data, copy=False)
        affine = src.transform
        rotated = affine.b != 0 or affine.d != 0
        left, bottom, right, top = src.bounds
        if not rotated:
            if affine.e > 0:
                data = data[:, ::-1, :]
            if affine.a < 0:
                data = data[:, :, ::-1]
        extent = (min(left, right), max(left, right), min(bottom, top), max(bottom, top))
        return (data[0] if single else np.moveaxis(data, 0, -1)), extent, src.crs, rotated


def stretch_rgb(
    rgb: ArrayLike, p_low: float = 2.0, p_high: float = 98.0, gamma: float = 1.0,
) -> NDArray[np.float64]:
    """逐波段拉伸到 [0, 1] 后应用 x**(1/gamma)，无效像元三通道均为 NaN。"""
    import numpy as np

    data = np.ma.masked_invalid(np.ma.asarray(rgb, dtype=float)).filled(np.nan)
    if data.ndim != 3 or data.shape[-1] != 3:
        raise ValueError("rgb 的形状须为 (H, W, 3)。")
    if not 0 <= p_low < p_high <= 100 or not math.isfinite(gamma) or gamma <= 0:
        raise ValueError("要求 0 ≤ p_low < p_high ≤ 100，且 gamma 为正的有限数。")
    valid = np.isfinite(data)
    result = np.full(data.shape, np.nan, dtype=float)
    for channel in range(3):
        band_valid = valid[..., channel]
        pixels = data[..., channel][band_valid]
        if pixels.size:
            low, high = np.percentile(pixels, [p_low, p_high])
            scaled = np.clip((pixels - low) / (high - low), 0, 1) if high > low else 0.5
            result[..., channel][band_valid] = scaled ** (1 / gamma)
    result[~valid.all(axis=-1)] = np.nan
    return result


def format_lonlat_ticks(
    ax: Axes, x_formatter: bool = True, y_formatter: bool = True, decimals: int = 1,
) -> None:
    """为本身使用十进制度的坐标轴标注经纬度，投影米轴需另行处理。"""
    from matplotlib.ticker import FuncFormatter

    if decimals < 0:
        raise ValueError("decimals 不能小于 0。")

    def longitude(value: float, _position: int | None) -> str:
        """将经度折回 ±180° 后添加方向。"""
        value = round((value + 180) % 360 - 180, decimals)
        suffix = "" if abs(value) in (0, 180) else ("E" if value > 0 else "W")
        return f"{abs(value):.{decimals}f}°{suffix}"

    def latitude(value: float, _position: int | None) -> str:
        """按纬度正负标注南北方向。"""
        value = round(value, decimals)
        suffix = "N" if value > 0 else ("S" if value < 0 else "")
        return f"{abs(value):.{decimals}f}°{suffix}"

    if x_formatter:
        ax.xaxis.set_major_formatter(FuncFormatter(longitude))
    if y_formatter:
        ax.yaxis.set_major_formatter(FuncFormatter(latitude))


def add_aligned_colorbar(
    fig: Figure, mappable: ScalarMappable | Artist, ax: Axes, orientation: str = "vertical",
    size: str | float = "3.5%", pad: float = 0.06, label: str | None = None,
    extend: str = "neither",
) -> Colorbar:
    """追加与绘图区对齐的色条，pad 为英寸，GeoAxes 也使用普通色条轴。"""
    from matplotlib.axes import Axes
    from matplotlib.transforms import Bbox
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    if orientation not in ("vertical", "horizontal"):
        raise ValueError("orientation 应为 'vertical' 或 'horizontal'。")
    side = "right" if orientation == "vertical" else "bottom"
    divider = make_axes_locatable(ax)
    cax = divider.append_axes(side, size=size, pad=pad, axes_class=Axes)
    map_locator = ax.get_axes_locator()
    assert map_locator is not None

    def aligned_locator(colorbar_ax: Axes, renderer: RendererBase) -> Bbox:
        """按应用纵横比后的绘图区定位色条，并保留英寸间距。"""
        ax.apply_aspect(map_locator(ax, renderer))
        bounds = ax.get_position()
        local_figure = colorbar_ax.figure
        width_in, height_in = local_figure.bbox.size / local_figure.dpi
        if orientation == "vertical":
            width = bounds.width * float(size[:-1]) / 100 if isinstance(size, str) else size / width_in
            return Bbox.from_bounds(bounds.x1 + pad / width_in, bounds.y0, width, bounds.height)
        height = bounds.height * float(size[:-1]) / 100 if isinstance(size, str) else size / height_in
        return Bbox.from_bounds(bounds.x0, bounds.y0 - pad / height_in - height, bounds.width, height)

    cax.set_axes_locator(aligned_locator)
    colorbar = fig.colorbar(mappable, cax=cax, orientation=orientation, extend=extend)
    if label:
        colorbar.set_label(label)
    return colorbar


def set_clipped_colorbar_ticks(
    colorbar: Colorbar, ticks: Sequence[float], clip_low: bool = False,
    clip_high: bool = False, fmt: str = "{:g}",
) -> None:
    """设置色条刻度。发生截尾的一侧须提供对应的范围端点刻度。"""
    values = tuple(ticks)
    labels = [fmt.format(value) for value in values]
    if values and (clip_low or clip_high):
        low = values.index(min(values))
        high = values.index(max(values))
        if clip_low and clip_high and low == high:
            raise ValueError("双侧截尾需要两个不同的端点刻度。")
        if clip_low:
            labels[low] = f"≤ {labels[low]}"
        if clip_high:
            labels[high] = f"≥ {labels[high]}"
    colorbar.set_ticks(values, labels=labels)


def plot_validation_scatter(
    ax: Axes, y_true: ArrayLike, y_pred: ArrayLike, mode: str = "auto", cmap: str = "viridis",
    show_stats: bool = True, stats_loc: str = "upper left", unit: str = "", rasterized: bool = True,
) -> tuple[ScalarMappable, dict[str, int | float]]:
    """绘制参考值与估计值，返回密度或点图层，以及以原始预测定义的精度指标。"""
    import numpy as np
    from matplotlib.offsetbox import AnchoredText

    if mode not in ("auto", "scatter", "density", "hexbin"):
        raise ValueError("mode 应为 auto、scatter、density 或 hexbin。")
    observed, predicted = (
        np.ma.masked_invalid(np.ma.asarray(values, dtype=float)).filled(np.nan)
        for values in (y_true, y_pred)
    )
    if observed.shape != predicted.shape:
        raise ValueError("参考值和估计值的形状须一致。")
    valid = np.isfinite(observed) & np.isfinite(predicted)
    x, y = observed[valid], predicted[valid]
    if not x.size:
        raise ValueError("没有同时有效的参考值与估计值。")
    low = float(min(x.min(), y.min()))
    high = float(max(x.max(), y.max()))
    margin = 0.04 * (high - low) if high > low else 0.05 * max(abs(low), 1.0)
    limits = (low - margin, high + margin)
    errors = y - x
    residuals = x - x.mean()
    sst = float(np.dot(residuals, residuals))
    mse = float(np.mean(errors ** 2))
    stats: dict[str, int | float] = {
        "N": int(x.size), "R2": float(1 - np.dot(errors, errors) / sst) if sst > 0 else math.nan,
        "RMSE": math.sqrt(mse), "MAE": float(np.mean(np.abs(errors))), "Bias": float(errors.mean()),
    }
    if mode == "auto":
        mode = "hexbin" if x.size > 5_000 and high > low else "scatter"
    if mode == "hexbin":
        mappable = ax.hexbin(
            x, y, gridsize=40, mincnt=1, extent=(*limits, *limits), cmap=get_cmap_safe(cmap),
            linewidths=0, rasterized=rasterized,
        )
    elif mode == "density":
        counts, x_edges, y_edges = np.histogram2d(x, y, bins=40, range=[limits, limits])
        x_bin = np.clip(np.searchsorted(x_edges, x, side="right") - 1, 0, 39)
        y_bin = np.clip(np.searchsorted(y_edges, y, side="right") - 1, 0, 39)
        density = counts[x_bin, y_bin]
        order = np.argsort(density, kind="stable")
        mappable = ax.scatter(x[order], y[order], c=density[order], cmap=get_cmap_safe(cmap),
                              s=9, linewidths=0, rasterized=rasterized)
    else:
        mappable = ax.scatter(x, y, s=10, color=SCI_PALETTE["blue"], alpha=0.7,
                              linewidths=0, rasterized=rasterized)

    ax.plot(limits, limits, "--", color=SCI_PALETTE["gray"], linewidth=0.9, label="1:1", zorder=3)
    if sst > 0:
        slope = float(np.dot(residuals, y - y.mean()) / sst)
        fitted = y.mean() + slope * (np.asarray([x.min(), x.max()]) - x.mean())
        ax.plot([x.min(), x.max()], fitted, color=SCI_PALETTE["brick"], linewidth=1.1, label="OLS", zorder=3)
    ax.set(xlim=limits, ylim=limits, aspect="equal",
           xlabel=f"Observed ({unit})" if unit else "Observed",
           ylabel=f"Predicted ({unit})" if unit else "Predicted")
    ax.set_adjustable("box")
    if show_stats:
        r2 = "NA" if math.isnan(stats["R2"]) else f"{stats['R2']:.3f}"
        suffix = f" {unit}" if unit else ""
        stats_text = "\n".join((
            f"$N$ = {stats['N']:,}", f"$R^2$ = {r2}", f"RMSE = {stats['RMSE']:.3g}{suffix}",
            f"MAE = {stats['MAE']:.3g}{suffix}", f"Bias = {stats['Bias']:+.3g}{suffix}",
        ))
        ax.add_artist(AnchoredText(stats_text, loc=stats_loc, prop={"size": "small"},
                                   pad=0.25, borderpad=0.55, frameon=False))
    return mappable, stats


def _series_colors(count: int, colors: Sequence[str] | None) -> list[str]:
    """保持跨图的统计系列配色顺序。"""
    palette = tuple(SCI_PALETTE.values()) if colors is None else colors
    if len(palette) == 0 or (colors is not None and len(colors) != count):
        raise ValueError("自定义 colors 须为每个系列提供一种颜色。")
    return [palette[index % len(palette)] for index in range(count)]


def make_grouped_bar(
    ax: Axes, categories: Sequence[str], series: Sequence[ArrayLike], labels: Sequence[str],
    ylabel: str = "", colors: Sequence[str] | None = None, annotate: bool = False,
    fmt: str = "{:.2f}", hatch_patterns: Sequence[str] | None = None,
    edgecolor: str = "black", linewidth: float = 0.6,
) -> list[BarContainer]:
    """绘制有描边的分组柱状图，标注缺失值时留空，返回各系列的柱组。"""
    import numpy as np

    groups, count = len(categories), len(series)
    if groups == 0 or count == 0 or len(labels) != count:
        raise ValueError("至少需要一个类别和一个系列，labels 数量须等于系列数。")
    data = [np.ma.masked_invalid(np.ma.asarray(values, dtype=float)).filled(np.nan) for values in series]
    if any(values.shape != (groups,) for values in data):
        raise ValueError("每个柱系列须为一维，且长度与 categories 相等。")
    if hatch_patterns is not None and len(hatch_patterns) != count:
        raise ValueError("hatch_patterns 数量须等于系列数。")

    positions = np.arange(groups)
    width = 0.8 / count
    bars = []
    for index, (values, label, color) in enumerate(zip(data, labels, _series_colors(count, colors))):
        offset = width * (index - (count - 1) / 2)
        container = ax.bar(positions + offset, values, width=width, label=label, color=color,
                           hatch=None if hatch_patterns is None else hatch_patterns[index],
                           edgecolor=edgecolor, linewidth=linewidth)
        if annotate:
            text = [fmt.format(value) if np.isfinite(value) else "" for value in values]
            ax.bar_label(container, labels=text, padding=2, fontsize="small")
        bars.append(container)
    ax.set_xticks(positions, labels=categories)
    ax.set_ylabel(ylabel)
    if annotate:
        ax.margins(y=0.14)
    return bars


def make_trend(
    ax: Axes, x: ArrayLike, y_series: Sequence[ArrayLike], labels: Sequence[str],
    y_err: Sequence[ArrayLike | None] | None = None, colors: Sequence[str] | None = None,
    xlabel: str = "", ylabel: str = "", linewidth: float = 1.4, band_alpha: float = 0.2,
) -> list[Line2D]:
    """绘制多序列及可选的逐点对称不确定性带，保留缺失值处的断线。"""
    import numpy as np

    coords = np.asanyarray(x)
    count = len(y_series)
    if coords.ndim != 1 or not coords.size or count == 0 or len(labels) != count:
        raise ValueError("要求非空一维 x，且 labels 数量与 y_series 一致。")
    if y_err is not None and len(y_err) != count:
        raise ValueError("y_err 数量须与 y_series 一致。")
    if not 0 <= band_alpha <= 1:
        raise ValueError("band_alpha 应在 [0, 1] 内。")

    ys = [np.ma.masked_invalid(np.ma.asarray(series, dtype=float)).filled(np.nan) for series in y_series]
    errors = [None] * count if y_err is None else [
        None if err is None else np.ma.masked_invalid(np.ma.asarray(err, dtype=float)).filled(np.nan)
        for err in y_err
    ]
    if any(values.shape != coords.shape for values in ys):
        raise ValueError("每条曲线的形状须与 x 相同。")
    if any(err is not None and (err.shape != coords.shape or np.any(err < 0)) for err in errors):
        raise ValueError("误差幅度须非负，形状须与 x 相同。")

    lines = []
    for values, error, label, color in zip(ys, errors, labels, _series_colors(count, colors)):
        line, = ax.plot(coords, values, color=color, linewidth=linewidth, label=label)
        lines.append(line)
        if error is not None:
            ax.fill_between(coords, values - error, values + error, color=color,
                            alpha=band_alpha, linewidth=0, zorder=line.get_zorder() - 1)
    ax.set(xlabel=xlabel, ylabel=ylabel)
    return lines


def make_heatmap(
    ax: Axes, matrix: ArrayLike, x_labels: Sequence[str] | None = None,
    y_labels: Sequence[str] | None = None, cmap: str = "viridis", cbar_label: str = "",
    annotate: bool = False, fmt: str = "{:.2f}", center_zero: bool = False,
) -> tuple[AxesImage, Colorbar]:
    """绘制带对齐色条的矩阵，保留缺失单元，并按背景亮度选择标注颜色。"""
    import numpy as np
    from matplotlib.colors import TwoSlopeNorm

    values = np.ma.masked_invalid(np.ma.asarray(matrix, dtype=float))
    if values.ndim != 2 or not values.size:
        raise ValueError("matrix 须为非空二维矩阵。")
    rows, columns = values.shape
    if (x_labels is not None and len(x_labels) != columns) or (y_labels is not None and len(y_labels) != rows):
        raise ValueError("行列标签数须与矩阵形状一致。")

    if center_zero:
        cmap_key = cmap.strip().casefold()
        if cmap_key.removesuffix("_r") not in _DIVERGING:
            if cmap_key != "viridis":
                warnings.warn(f"居中色标使用发散色表，已将 {cmap!r} 换为 'vik'。", stacklevel=2)
            cmap = "vik"
        span = float(np.max(np.abs(values.compressed()), initial=0)) or 1.0
        norm = TwoSlopeNorm(vmin=-span, vcenter=0, vmax=span)
    else:
        norm = None
    palette = get_cmap_safe(cmap).with_extremes(bad="#A8ADB3")
    image = ax.imshow(values, cmap=palette, norm=norm, interpolation="nearest", rasterized=True)
    colorbar = add_aligned_colorbar(ax.figure, image, ax, label=cbar_label)
    ax.set_xticks(range(columns), labels=x_labels)
    ax.set_yticks(range(rows), labels=y_labels)
    if annotate:
        for row, column in zip(*np.nonzero(~np.ma.getmaskarray(values))):
            value = float(values[row, column])
            rgb = np.asarray(palette(image.norm(value))[:3])
            linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
            luminance = float(np.dot(linear, [0.2126, 0.7152, 0.0722]))
            ax.text(column, row, fmt.format(value), ha="center", va="center", fontsize="small",
                    color="black" if luminance > 0.179 else "white")
    return image, colorbar


def save_figure(
    fig: Figure, out_path: str | Path, formats: Sequence[str] = ("png", "pdf"),
    dpi: int = 300, preview_dpi: int | None = 180, tight: bool = True, pad_inches: float = 0.04,
) -> tuple[Path, ...]:
    """导出固定物理画布及独立预览，tight 检查边距，绝不改变成品尺寸。"""
    import matplotlib as mpl

    if dpi <= 0 or (preview_dpi is not None and preview_dpi <= 0) or pad_inches < 0:
        raise ValueError("DPI 须为正数，pad_inches 须非负，preview_dpi=None 可跳过预览。")
    requested = tuple(dict.fromkeys(ext.lower().lstrip(".") for ext in formats))
    supported = fig.canvas.get_supported_filetypes()
    unknown = [ext for ext in requested if ext not in supported]
    if not requested or unknown:
        raise ValueError(f"无可用目标格式或后端不支持格式 {unknown}。")

    stem = Path(out_path).expanduser().resolve()
    if stem.suffix.lower().lstrip(".") in supported:
        stem = stem.with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)
    if tight:
        fig.canvas.draw()
        extent = fig.get_tightbbox()
        if extent is not None:
            width, height = fig.get_size_inches()
            left, right = extent.x0, width - extent.x1
            bottom, top = extent.y0, height - extent.y1
            if min(left, right, bottom, top) < pad_inches:
                warnings.warn("画布边缘留白不足或内容可能被裁切，请调整布局并检查预览。", stacklevel=2)
            dimensions = (
                ("横向", extent.width / width, max(left, right)),
                ("纵向", extent.height / height, max(bottom, top)),
            )
            excess = [f"{axis}内容占 {coverage:.1%}，最大白边 {margin:.2f} in"
                      for axis, coverage, margin in dimensions if coverage < 0.78 and margin > 0.45]
            if excess:
                warnings.warn(f"画布白边过宽（{' / '.join(excess)}）。请保持成品宽度，收紧画布高度或外边距。",
                              stacklevel=2)

    targets = [(stem.parent / f"{stem.name}.{ext}", ext, dpi) for ext in requested]
    if preview_dpi is not None:
        targets.append((stem.parent / f"{stem.name}.preview.png", "png", preview_dpi))
    with mpl.rc_context({"savefig.bbox": None, "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"}):
        for path, ext, export_dpi in targets:
            fig.savefig(path, format=ext, dpi=export_dpi, bbox_inches=None)
            details = ""
            if ext == "png":
                with path.open("rb") as handle:
                    header = handle.read(24)
                pixel_width, pixel_height = struct.unpack(">II", header[16:24])
                details = f" | {pixel_width} × {pixel_height} px"
            size_mb = path.stat().st_size / 1_000_000
            print(f"{path}{details} | {size_mb:.2f} MB")
            if ext in ("pdf", "svg", "svgz", "eps", "ps", "pgf") and size_mb > 15:
                warnings.warn(f"矢量输出 {path.name} 超过 15 MB，请检查密集图层的 rasterized=True。", stacklevel=2)
    return tuple(path for path, _, _ in targets)


def _doctor() -> int:
    """报告解释器、核心依赖、可选依赖及 Matplotlib 识别的字体。"""
    print(f"Python {platform.python_version()} | {sys.executable}")
    print("核心依赖（实际导入）")
    missing_core = False
    for name in ("numpy", "matplotlib"):
        try:
            module = _require(name)
            print(f"  {name}: {module.__version__}")
        except Exception as exc:
            print(f"  {name}: 不可用 | {exc}")
            missing_core = True

    print("可选依赖（检查安装，不导入）")
    for module_name, dist_name in _OPTIONAL.items():
        try:
            if importlib.util.find_spec(module_name) is None:
                print(f"  {module_name}: 未安装")
                continue
            version = importlib.metadata.version(dist_name)
            print(f"  {module_name}: {version or '已发现模块，版本元数据不可用'}")
        except importlib.metadata.PackageNotFoundError:
            print(f"  {module_name}: 已发现模块，版本元数据不可用")
        except (ImportError, ValueError, OSError) as exc:
            print(f"  {module_name}: 无法检查 | {exc}")

    print("常用字体（Matplotlib 可用家族）")
    try:
        fonts = _available_fonts()
        print("  已找到 " + ("、".join(name for name in _FONT_PROBES if name.casefold() in fonts) or "无"))
        print("  未找到 " + ("、".join(name for name in _FONT_PROBES if name.casefold() not in fonts) or "无"))
        print(f"  字体家族总数 {len(fonts)}")
    except Exception as exc:
        print(f"  无法扫描字体 | {exc}")
    return int(missing_core)


def _inspect_raster(path: Path) -> None:
    """逐波段体检，限制抽样数组的最大边长。"""
    import numpy as np

    rasterio = _require("rasterio")
    with rasterio.open(path) as src:
        affine = src.transform
        rotated = affine.b != 0 or affine.d != 0
        height, width = _reduced_shape(src.height, src.width, _RASTER_SAMPLE_SIDE)
        sampled = (height, width) != (src.height, src.width)
        print(f"栅格 | CRS: {src.crs or '缺失'} | 宽×高: {src.width}×{src.height} | 波段: {src.count}")
        print(f"分辨率 (x, y): {src.res} | bounds (左, 下, 右, 上): {tuple(src.bounds)}")
        print(f"transform (a, b, c, d, e, f): {tuple(affine)[:6]} | 旋转/倾斜: {'是' if rotated else '否'}")
        print(f"NoData（按波段）: {src.nodatavals}")
        print(f"统计: {'最近邻降采样估算' if sampled else '全像元'} ({width}×{height})")
        for band in src.indexes:
            values = np.ma.masked_invalid(src.read(band, out_shape=(height, width), masked=True)).compressed()
            fraction = values.size / (width * height)
            if values.size and not np.iscomplexobj(values):
                quantiles = ", ".join(f"{value:.8g}" for value in np.percentile(values, (2, 50, 98)))
            else:
                quantiles = "无可用实数"
            print(f"  波段 {band} ({src.dtypes[band - 1]}): 有效 {fraction:.2%} | P02/P50/P98: {quantiles}")


def _sample_data_array(var: DataArray) -> tuple[NDArray[Any], bool]:
    """在加载数据前对较大的变量沿各维按步长抽样。"""
    indexes: dict[str, slice] = {}
    sizes = dict(var.sizes)
    if var.size > _NC_SAMPLE_LIMIT:
        lengths = sizes.copy()
        steps = dict.fromkeys(lengths, 1)
        while math.prod(lengths.values()) > _NC_SAMPLE_LIMIT:
            dim = max(lengths, key=lengths.__getitem__)
            steps[dim] *= 2
            lengths[dim] = (sizes[dim] + steps[dim] - 1) // steps[dim]
        indexes = {dim: slice(None, None, step) for dim, step in steps.items() if step > 1}
    return var.isel(indexes).values, bool(indexes)


def _coordinate_type(name: str, coord: DataArray) -> str | None:
    """通过坐标名与 CF 属性识别经纬度，避免将平面 x/y 误判为度。"""
    standard_name = str(coord.attrs.get("standard_name", "")).lower()
    units = str(coord.attrs.get("units", "")).lower().replace(" ", "_")
    if name.lower() in ("lat", "latitude", "nav_lat", "xlat") or standard_name == "latitude" or units in (
        "degree_north", "degrees_north", "degree_n", "degrees_n", "degreen", "degreesn",
    ):
        return "纬度"
    if name.lower() in ("lon", "long", "longitude", "nav_lon", "xlong") or standard_name == "longitude" or units in (
        "degree_east", "degrees_east", "degree_e", "degrees_e", "degreee", "degreese",
    ):
        return "经度"
    return None


def _inspect_netcdf(path: Path, layer: str | None) -> None:
    """按 CF 元数据检查维度、坐标方向和变量的有效范围。"""
    import numpy as np

    xr = _require("xarray")
    options = {"group": layer} if layer is not None else {}
    try:
        dataset = xr.open_dataset(path, mask_and_scale=True, **options)
    except (ValueError, ImportError, OSError) as exc:
        raise ValueError(
            f"无法打开 NetCDF（{exc}）。请核对文件、分组和 CF 时间编码。"
            "如缺后端，可运行 python -m pip install netCDF4 cftime"
        ) from exc

    with dataset as ds:
        print(f"NetCDF | dims: {dict(ds.sizes)}")
        print("coords:")
        for name, coord in ds.coords.items():
            unit = coord.attrs.get("units", coord.encoding.get("units", "—"))
            description = f"  {name}: dims={coord.dims}, shape={coord.shape}, units={unit}"
            kind = _coordinate_type(str(name), coord)
            if kind and coord.dtype.kind in "biuf":
                values, sampled = _sample_data_array(coord)
                finite = values[np.isfinite(values)]
                description += f" | {kind}{'（抽样）' if sampled else ''}"
                if finite.size:
                    low, high = float(finite.min()), float(finite.max())
                    description += f" [{low:.8g}, {high:.8g}]"
                    if kind == "纬度" and coord.ndim == 1 and finite.size > 1:
                        if np.all(finite[1:] < finite[:-1]):
                            description += " | 纬度降序"
                        elif np.all(finite[1:] > finite[:-1]):
                            description += " | 纬度升序"
                        else:
                            description += " | 纬度非严格单调"
                    elif kind == "纬度" and coord.ndim > 1:
                        description += " | 多维坐标，检查网格索引与方向"
                    if kind == "经度" and 0 <= low <= 360 and 180 < high <= 360:
                        description += " | 检出 0–360° 经度表示"
                else:
                    description += " | 无有效坐标"
            print(description)
        print("data_vars:")
        for name, var in ds.data_vars.items():
            unit = var.attrs.get("units", var.encoding.get("units", "—"))
            description = f"  {name}: shape={var.shape}, dtype={var.dtype}, units={unit}"
            if var.dtype.kind in "biuf":
                values, sampled = _sample_data_array(var)
                finite = values[np.isfinite(values)]
                value_range = f"[{finite.min():.8g}, {finite.max():.8g}]" if finite.size else "无有效值"
                description += f" | 有效值域{'（抽样）' if sampled else ''}: {value_range}"
            if grid_mapping := var.attrs.get("grid_mapping", var.encoding.get("grid_mapping")):
                description += f" | grid_mapping={grid_mapping}"
            print(description)


def _inspect_vector(path: Path, layer: str | None) -> None:
    """报告空间元数据和前五个实数属性的缺失率与值域。"""
    import numpy as np

    geopandas = _require("geopandas")
    options = {"layer": layer} if layer is not None else {}
    frame = geopandas.read_file(path, **options)
    geometry = frame.geometry
    counts = {str(key) if key is not None else "缺失": int(value)
              for key, value in geometry.geom_type.value_counts(dropna=False).items()}
    bounds = tuple(float(v) for v in frame.total_bounds)
    print(f"矢量 | CRS: {frame.crs or '缺失'} | 要素: {len(frame)} | 几何类型: {counts}")
    print(f"total_bounds (左, 下, 右, 上): {bounds if np.all(np.isfinite(bounds)) else '无有效几何范围'}")
    print(f"字段: {list(frame.columns)}")
    print("数值字段（至多五项）:")
    numeric = frame.select_dtypes(include="number").select_dtypes(exclude="complex")
    for name in numeric.columns[:5]:
        values = numeric[name].to_numpy(dtype=float, na_value=np.nan)
        finite = values[np.isfinite(values)]
        missing = f"{1 - finite.size / values.size:.2%}" if values.size else "无记录"
        value_range = f"[{finite.min():.8g}, {finite.max():.8g}]" if finite.size else "无有效值"
        print(f"  {name}: 缺失率 {missing} | 值域 {value_range}")


def _inspect(path: Path, layer: str | None) -> None:
    """按文件后缀分发数据体检，并拒绝无效的层名用法。"""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"找不到本地数据文件 {path}")
    suffix = path.suffix.lower()
    print(f"文件: {path}")
    if suffix in _RASTER_EXTS:
        if layer is not None:
            raise ValueError("--layer 用于矢量图层或 NetCDF 分组。")
        _require("numpy")
        _inspect_raster(path)
    elif suffix in _NETCDF_EXTS:
        _require("numpy")
        _inspect_netcdf(path, layer)
    elif suffix in _VECTOR_EXTS:
        _require("numpy")
        _inspect_vector(path, layer)
    else:
        raise ValueError(f"不支持的后缀 {suffix!r}。支持 GeoTIFF/IMG/VRT、NC/NC4、SHP/GeoJSON/GPKG/FGB。")


def main(argv: Sequence[str] | None = None) -> int:
    """处理 CLI 参数，并将可诊断的失败转换为简洁的退出状态。"""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="检查 Python、依赖与字体")
    inspect = subparsers.add_parser("inspect", help="检查本地栅格、NetCDF 或矢量")
    inspect.add_argument("path", type=Path, help="数据文件路径")
    inspect.add_argument("--layer", help="矢量图层名或 NetCDF 分组名")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return _doctor()
    try:
        _inspect(args.path, args.layer)
    except _DependencyError as exc:
        print(f"依赖错误: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"体检失败: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if not stream.isatty():
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
