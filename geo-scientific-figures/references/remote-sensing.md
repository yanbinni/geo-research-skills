# 遥感影像、栅格专题图与 NetCDF

## GeoTIFF 与空间网格

1. 用 `inspect` 记录 CRS、尺寸、分辨率、bounds、transform、NoData、各波段有效比例和 P02/P50/P98。三角形或黑边先核查掩膜，用地标检查方向和空间位置。
2. `read_raster_for_plot(path, bands=1, max_dim=2000)` 以实际 bounds 返回 `(左, 右, 下, 上)`、CRS、旋转标志和 `MaskedArray`。单整数波段返回 `(H, W)`，序列返回 `(H, W, C)`。未旋转数据已按北在上、西在左整理，显示用 `origin="upper"`。
3. 大图按长宽比用 `out_shape` 降采样。工具箱使用 Rasterio 默认最近邻，适用于显示和分类 ID。连续影像重采样按需要选 `bilinear` 或 `average`，使 NoData 与有效像元分别处理。定量分析、面积计算和显著性检验使用科学分析网格。
4. `transform.b != 0` 或 `transform.d != 0` 表示网格旋转或倾斜。`bounds` 是轴对齐外包框，`imshow(extent=...)` 会错放像元。先用 `WarpedVRT` 或 `rasterio.warp.reproject` 建立轴对齐目标网格，或用 affine 计算像元角点并以 `pcolormesh()` 显示实际网格。
5. 显示用预览网格时，重新计算分辨率或像元角点需使用 `src.transform * src.transform.scale(src.width / width, src.height / height)`。仿射规则网格的外边界通常保持原范围。GCPS、RPC 或曲线网格须采用其原始地理定位机制。[Rasterio 重采样](https://rasterio.readthedocs.io/en/stable/topics/resampling.html)

绘制同 CRS 栅格与矢量时，用显式重投影与共同范围。有效零值保持色表中的对应颜色。按研究区范围分开外部纯白或透明背景与内部缺测。连续地图的内部显著缺测使用中性浅灰并在图注说明。零值色接近白色时，可加细线标出研究区边界。显示截尾保留原始数据用于统计，按 [色条截尾表达](style-and-export.md#色条截尾表达) 标注端点和比例。

## 真彩色和假彩色

| 目的 | RGB 通道顺序 | 注意 |
| --- | --- | --- |
| 真彩色 | Red / Green / Blue | 确认传感器对应波段及反射率缩放 |
| 标准植被假彩色 | NIR / Red / Green | 说明植被呈红色，便于解读 |
| 常用 SWIR 组合 | SWIR2 / NIR / Red 或 SWIR1 / NIR / Green | 按火烧迹地、地质或水分任务选择并在图注列波段 |

`stretch_rgb()` 默认逐波段对有效值使用 2%–98% 分位数，裁剪至 `[0, 1]` 后应用 `x ** (1 / gamma)`。`gamma > 1` 提亮中间调。任何通道无效时三通道输出 `NaN`，以显式 alpha 生成透明区。时相或产品对比先确定共享分位数阈值和 gamma，再统一应用，避免每景独立拉伸掩盖真实变化。

```python
import numpy as np
from geo_fig_kit import read_raster_for_plot, stretch_rgb

# band_ids 来自当前传感器的波段元数据。
rgb, extent, crs, rotated = read_raster_for_plot(image_path, bands=band_ids)
if crs is None or rotated:
    raise ValueError("核对 CRS，并先把旋转影像转换为正向规则网格")
scaled = stretch_rgb(rgb, p_low=2, p_high=98, gamma=1.1)
alpha = np.isfinite(scaled).all(axis=-1)
rgba = np.dstack([np.nan_to_num(scaled), alpha.astype(float)])
ax.imshow(rgba, extent=extent, origin="upper", interpolation="nearest", rasterized=True)
```

## LULC 语义分类与图例

| 地类 | 参考颜色 | 印刷时可辅助 |
| --- | --- | --- |
| 林地 | `#286143` | 边界或粗线纹理 |
| 灌丛 | `#72863D` | 点纹 |
| 草地 | `#B5C675` | 稀斜线 |
| 农田 | `#DFC46A` | 竖纹 |
| 水体 | `#287AA8` | 水平纹理 |
| 湿地 | `#4DB3AD` | 短虚线纹理 |
| 建成区 | `#B65D4D` | 交叉纹 |
| 裸地 | `#B98D68` | 稀点纹 |
| 冰雪 | `#F4F6FA` | 灰色轮廓 |

编码取自数据图例。对不连续或有空缺的源 ID，按元数据映射到紧邻索引 `0…K-1`。先校验未知码并保留原掩膜。绘图使用 `ListedColormap`、`BoundaryNorm` 和离散色块图例，禁止连续 colorbar。成组制图把同一类型对应到相同颜色和顺序。

```python
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

# codes、names、colors 按原数据图例定义。classes 为读出的掩膜数组。
# study_mask 为同网格布尔数组，True 表示研究区内部。
source_missing = np.ma.getmaskarray(classes)
display = np.ma.masked_all(classes.shape, dtype=np.int16)
for index, code in enumerate(codes):
    display[study_mask & np.ma.filled(classes == code, False)] = index
if np.any(study_mask & np.ma.getmaskarray(display) & ~source_missing):
    raise ValueError("图例编码缺少有效地类")
entries = list(zip(names, colors))
inside_missing = study_mask & source_missing
if inside_missing.any():
    display[inside_missing] = len(entries)
    entries.append(("无数据", "#D9D9D9"))
palette = ListedColormap([color for _, color in entries]).with_extremes(bad="none")
norm = BoundaryNorm(np.arange(palette.N + 1) - 0.5, palette.N)
ax.imshow(display, extent=extent, origin="upper", cmap=palette, norm=norm,
          interpolation="nearest", rasterized=True)
handles = [Patch(facecolor=color, edgecolor="0.3", linewidth=0.45, label=name)
           for name, color in entries]
ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.05, 1))
```

灰度打印需复核类别间对比。可在矢量面使用描边、不同 hatch，或叠加类别掩膜纹理。给图例色块相同的描边与纹理。高密度纹理可单独栅格化。

## 变化、距平、趋势与显著性

- **物理主导语义优先于偶发极值。** 若 NPP 等生产力指标主体非负，且仅有少量略为负值并已核实来自边缘效应或噪声，默认沿用顺序色表与 `Normalize(vmin=0, vmax=…)`，保留主体范围的颜色对比。显示下限与统计质控分别记录，核对实际负值比例及来源。
- 对有正负方向的净交换、变化、距平或趋势，先定义方向、参考期、物理单位和有效像元交集。用 `TwoSlopeNorm(vmin=…, vcenter=0, vmax=…)` 将零对齐中性色。采用其他参考值时标明含义。确保 `vmin < vcenter < vmax`，物理中心两侧的阈值由同组对比口径确定。
- 并排地图若需比较同幅增减，采用一致上下限。单图和套图的色条默认平头 `extend="neither"`，对称发散范围也沿用此规则。用原始分析网格中质控后的研究区有效像元统计严格低于下限或高于上限的比例，仅在真实溢出侧的端点刻度标 `≤` 或 `≥`。图注注明变量、方向、阈值及各侧占比。只有用户明确要求时，才在真实溢出侧加传统尖端。
- 统计显著性层与数值网格严格对齐。取有效数据和通过检验的掩膜交集，例如 `(p < 0.05)`。在像元中心画稀疏 stippling，或用 `contourf` 的 hatch 表示相连区域。QA 核对示例真阳性区域和掩膜边界。
- 图注注明检验方法、样本数或时段、显著性阈值、是否校正多重比较、打点降采样方式。显著性与效应量分别表达。

```python
import numpy as np
from matplotlib.colors import ListedColormap, TwoSlopeNorm
from geo_fig_kit import get_cmap_safe

# x、y 是规则网格 1D 像元中心。change 与 p_value 同网格，同方向。
# study_mask 为同网格布尔数组，True 表示研究区内部。
field = np.ma.masked_where(~study_mask, np.ma.masked_invalid(np.ma.asarray(change, dtype=float)))
inside_missing = study_mask & np.ma.getmaskarray(field)
if inside_missing.any():
    missing_layer = np.ma.masked_where(~inside_missing, np.ones(field.shape))
    gray = ListedColormap(["#D9D9D9"]).with_extremes(bad="none")
    ax.imshow(missing_layer, extent=extent, origin="upper", cmap=gray,
              interpolation="nearest", rasterized=True)
# span 是同组图共用的正值，依据数据范围或物理阈值预先确定。
norm = TwoSlopeNorm(vmin=-span, vcenter=0, vmax=span)
image = ax.imshow(field, extent=extent, origin="upper", norm=norm,
                  cmap=get_cmap_safe("vik").with_extremes(bad="none"),
                  interpolation="nearest", rasterized=True)
significant = ~np.ma.getmaskarray(field) & np.ma.filled(np.ma.asarray(p_value) < 0.05, False)
rows, cols = np.nonzero(significant[::step, ::step])  # step 为经预览确认的稀疏步长
ax.scatter(x[cols * step], y[rows * step], s=1.0, c="0.17", linewidths=0, rasterized=True)
```

### 可选的统计摘要框

需要报告区域均值、总量或有效覆盖率时，可调用 `add_stats_box()`。使用已核验的单位与统计口径，均值和总量按需要采用像元面积加权。只在确认有空白的角落使用，避免盖住研究区主体、色条、比例尺或指北针。空间不足时把摘要放到图注。

```python
from geo_fig_kit import add_stats_box

add_stats_box(ax, ["Mean: 412.5 g C m⁻² yr⁻¹", "Total: 2.71 Tg C yr⁻¹"], loc="upper left")
```

## DEM 与山体阴影

`LightSource.hillshade()` 统计坡度需可靠的 x/y 间距。先把 DEM 整理为正北向上、规则米制网格，把高程与 `dx`、`dy` 化为同一线性单位。经纬度网格的度数不能直接与垂直米量混算。掩膜边缘可扩一像元以排除邻域传播伪影。

```python
import numpy as np
from matplotlib.colors import LightSource

elevation = np.ma.masked_invalid(np.ma.asarray(dem, dtype=float))
light = LightSource(azdeg=315, altdeg=45)
shade = light.hillshade(elevation, dx=dx_m, dy=dy_m, vert_exag=1.0)
ax.imshow(shade, cmap="gray", extent=extent, origin="upper", rasterized=True)
ax.imshow(theme, cmap=theme_cmap, norm=theme_norm, extent=extent, origin="upper",
          alpha=0.65, rasterized=True)
```

叠加前确认 `theme` 与阴影同一网格、同一方向。保留专题本身的 `norm` 和色条说明。半透明混合会改变视觉颜色，需准确读色时降低阴影存在感，或分栏显示原专题值与地形参考。

## xarray / NetCDF

- 检查 `dims`、真实 `coords`、瓦片经纬方向、`units`、`grid_mapping`、`_FillValue`、`scale_factor` 和 `add_offset`。按 CF 解码后避免重复缩放。[xarray `open_dataset`](https://docs.xarray.dev/en/stable/generated/xarray.open_dataset.html)
- 纬度为降序时，若数组第一行在北侧，规则栅格可用 `origin="upper"`。也可 `sortby("lat")` 升序后使用 `origin="lower"`。只选一种方向处理，并对照地标验证。
- 一维 `[0, 360)` 经度可改写为 `[−180, 180)`，再排序并核对周期重复端点。例如 `da.assign_coords(lon=(da.lon + 180) % 360 - 180).sortby("lon")`。若同时有 0° 与 360°，核对数据后仅保留一份。二维曲线经纬网不能沿一维经度直接重排，使用网格角点和适当的网格绘制或重网格。
- `imshow()` 的 `extent` 使用像元边界。CF 提供 `bounds` 时优先使用；等距中心可向外推半个像元。不等距或曲线网格用 `pcolormesh()` 和实际坐标。
- 用 `sel(time=...)` 或 `isel(time=...)` 显式挑选切片，核对 `calendar`、时区约定、时间边界、单位以及月平均或累积语义。序列比较先统一时间基准和 K/℃ 等量纲。
- 多文件或长时间序列宜先裁剪空间与时间维，再加载或按需分块。CLI 的大变量范围来自步长抽样，极值需在相关切片单独核实。
