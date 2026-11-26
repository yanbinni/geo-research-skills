# 地图投影、边界与定位图

## 先核对 CRS、目标范围与投影

GRS80、WGS 84、CGCS2000 等基准涉及来源精度和叠加误差。检查坐标参考系和单位，记录数据 CRS、目标 CRS、图层范围、影像外包框与可见布局。GeoPandas 的 `set_crs()` 仅赋予已知的源 CRS，坐标转换使用 `to_crs()`。Cartopy 的 `projection=` 决定画板投影，`transform=` 或 `add_geometries(..., crs=...)` 声明传入坐标系。

| 尺度或目的 | 常用投影 | 需要核验 |
| --- | --- | --- |
| 全球面积专题分布 | Equal Earth 等积 | 中央经线、陆地断裂、跨日期变更线拆分、极区表现 |
| 全球概览 | Robinson 折衷 | 形状与面积的折衷，避免从视觉面积推导统计结论 |
| 中纬度区域面积比较 | Albers Equal Area | 标准纬线和中央经线适配研究区 |
| 中纬度区域形态或角度表达 | Lambert Conformal Conic | 检查标准纬线、收敛角和区域内尺度变化 |
| 单带局部地形、样点或距离 | UTM 对应分带和半球，或可信地方投影 | 单位、投影边缘、局部形变与网格北偏转 |
| 小范围经纬度示意 | Plate Carrée 或普通经纬度轴 | 明示角度轴及宽高比例，不在图上读平面距离 |

禁止使用 Plate Carrée 或 Web Mercator 画全球面积专题分布。面积统计使用相应等积投影或按像元真实面积加权。经纬度可视窗口遇到日期变更线时，应先整理矢量切分和栅格的经度包装，再统一中央经线。

## 封闭地图框与经纬标注

### Cartopy

以下函数接收已核实 CRS 的用户本地 GeoDataFrame，以及在 EPSG:4326 下给出的 `(西, 东, 南, 北)`。范围为区域性、未跨日期变更线。输入矢量的来源需满足下文审图约束。

```python
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LatitudeFormatter, LatitudeLocator, LongitudeFormatter, LongitudeLocator
from matplotlib import rcParams
from geo_fig_kit import style_map_ax


def draw_geographic_layer(ax, layer, extent, linewidth=0.7, label_grid=True):
    if layer.crs is None:
        raise ValueError("图层缺少已核实的 CRS")
    lonlat = ccrs.PlateCarree()
    geometry = layer.to_crs("EPSG:4326").geometry.dropna()
    ax.set_extent(extent, crs=lonlat)
    ax.add_geometries(geometry, crs=lonlat, facecolor="none",
                      edgecolor="#35414A", linewidth=linewidth)
    style_map_ax(ax, linewidth=linewidth)
    grid = ax.gridlines(crs=lonlat, draw_labels=label_grid, x_inline=False, y_inline=False,
                        linewidth=0.4, color="0.64", alpha=0.55, linestyle="--")
    grid.top_labels = grid.right_labels = False
    grid.xlocator, grid.ylocator = LongitudeLocator(nbins=4), LatitudeLocator(nbins=4)
    grid.xformatter = LongitudeFormatter(number_format=".1f")
    grid.yformatter = LatitudeFormatter(number_format=".1f")
    grid.xlabel_style = {"size": rcParams["xtick.labelsize"]}
    grid.ylabel_style = {"size": rcParams["ytick.labelsize"]}
    grid.rotate_labels = False
```

普通地图使用四边框，非矩形投影沿其投影外缘闭合。Cartopy `Gridliner` 的文字由经纬网与外框交点生成，`tick_params()` 控制的轴刻度是另一层。避免两套标签重复，渲染后按投影删去拥挤标签。显示同 CRS 的北向正规则栅格时给 `imshow()` 增加 `transform=` 和原始 `extent=`。跨投影画图时宜先设定视图范围，再让 Cartopy 重采样，或预先把影像重投影到目标网格。[Cartopy 网格与标注](https://cartopy.readthedocs.io/stable/matplotlib/gridliner.html)

### 无 Cartopy 的 Matplotlib / GeoPandas

```python
from math import cos, radians
from matplotlib.ticker import MaxNLocator
from geo_fig_kit import format_lonlat_ticks, style_map_ax


def draw_local_lonlat(ax, layer, extent):
    if layer.crs is None:
        raise ValueError("图层缺少已核实的 CRS")
    west, east, south, north = extent
    if not (-180 <= west < east <= 180 and -90 < south < north < 90):
        raise ValueError("经纬度范围须升序、未跨日期变更线且避开极点")
    layer.to_crs("EPSG:4326").plot(ax=ax, facecolor="none", edgecolor="#35414A", linewidth=0.7)
    ax.set(xlim=(west, east), ylim=(south, north))
    ax.set_aspect(1 / cos(radians((south + north) / 2)))  # 区域经纬网的近似屏显宽高
    style_map_ax(ax)
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    format_lonlat_ticks(ax, decimals=1)
    ax.grid(color="0.85", linewidth=0.4, linestyle="--")
```

纯栅格可跳过 GeoPandas，使用 `read_raster_for_plot()` 和 `imshow(..., origin="upper", extent=extent)`。前提是正北规则网格、经纬度数据且 CRS 已核实。以已知地标检查东向在右、北向在上，确认经纬范围和 W/E、S/N 后缀。投影米制轴标注如 `Easting (m)`、`Northing (m)`，不直接套 `format_lonlat_ticks()`。需要保留投影米轴和经纬标签时，显式投影经纬线并在与可见边框的交点注记。

## 比例尺与指北针

- 局部合适的米制投影可在指定图面位置用投影距离绘制比例尺。核对轴单位、投影尺度因子和最终摆放位置，按图面大小选取易读的 km 整数。比例尺长度可用反投影后 `pyproj.Geod.inv()` 的椭球测地距离交叉核验。
- 经纬度轴上，角度差与米的换算随纬度和方向变化。小范围确需比例尺时，以拟放位置的纬度为基准，在同一椭球上计算两端点之间的测地距离，并注明局部有效性。跨大纬度、EPSG:4326 大跨度、跨投影分区或全局投影禁放一根通用线性比例尺。
- 使用 `matplotlib-scalebar` 时核实每轴单位对应的距离、坐标轴纵横比及缩放。缺包时可在米制轴用两端点画固定数据长度的线，并在上方标明换算后的 km。
- 只有局部真北沿图面竖直方向时，直接画竖直北箭头。对弯曲经线、倾斜图幅或网格北与真北不同的投影，在箭头锚点取一个小的地理向北偏移，把两点投影后用向量定角。若箭头表示网格北则标注 `GN`；方向随位置明显变化时保留经纬网并省略箭头。

## 中国范围的底图与审图

- 涉及中国全图、中国国界、南海九段线或争议边界表达，使用用户提供、可核对来源的合规标准审图矢量和线划。禁止默认调用 Cartopy 的 Natural Earth 图层，也避免通过 `coastlines()`、`BORDERS` 或含边界的默认底图间接引入相同线划。
- 确认底图材料的来源、适用范围和审图信息，按适用要求标注来源与审图号。保留经核验的边界线型和相关注记。裁剪、重投影、改动图面或合成后，确认该成品的审图要求和适用性。[自然资源部标准地图服务系统](https://bzdt.tianditu.gov.cn/) · [公开地图内容表示规范](https://www.fmprc.gov.cn/web/wjb_673085/zzjg_673183/bjhysws_674671/bhflfg/dtdmxgfl/202303/P020230313585504979937.pdf)
- 缺底图时暂停地图部分。说明现有数据无法验证国界和岛屿表示，请用户提供适用图层、其 CRS、来源及审图信息。其余已具备数据的统计面板可继续准备。
- 需要南海诸岛小图时，从同套合规数据建立独立封闭 inset，按合规底图指定范围呈现岛屿、线划、图式和标注。为小图及审图信息预留确切空间，检查无任意裁剪、缩并、简化、遮盖或线划变化。小图与研究区定位图承担不同功能，应按实际图式分开布置。

## 研究区概况、定位与局部放大

### 研究区概况图与 Locator Inset

1. 主图使用研究区和相关地物的细节，表达研究区边界、样点或地貌。明确主图 CRS、范围和专题单位。
2. 在主图的空角或独立图槽设 inset。小图淡化区域背景，用主图一致的边界色标出研究区几何或覆盖框。小范围难辨时用点与短标签，图注明确标记语义。
3. 定位图可用不同投影和比例；投影后计算边框或几何范围。主图在曲线投影下的范围框可沿边界加密后转换，不能将两组范围值直接套入不同的 CRS。

```python
# fig、ax、region、study 已从已核实的本地数据准备好。
# context_extent 是区域经纬度窗口，study_extent 是主图经纬度窗口。
locator = ax.inset_axes([0.69, 0.67, 0.28, 0.29], projection=ccrs.PlateCarree())
draw_geographic_layer(ax, study, study_extent)
draw_geographic_layer(locator, region, context_extent, linewidth=0.55, label_grid=False)
locator.add_geometries(study.to_crs("EPSG:4326").geometry.dropna(), ccrs.PlateCarree(),
                       edgecolor="#AE4938", facecolor="none", linewidth=1.0)
```

小图过密时保留封闭框，精简重复刻度和网格。示例通过 `label_grid=False` 隐藏小图重复标注。把小图移到独立图槽可防止覆盖主图数据。

### Zoom-in Inset

同坐标系可直接标记主图的缩放窗口。下例用于普通 Matplotlib 轴，`draw_layers()` 接收坐标轴和在同一 CRS 下的图层。裁剪区使用主图数据坐标，线框端点随轴位置更新。

```python
from geo_fig_kit import style_map_ax

zoom = ax.inset_axes([0.64, 0.07, 0.32, 0.32])
draw_layers(zoom)
zoom.set(xlim=(xmin, xmax), ylim=(ymin, ymax), aspect="equal")
style_map_ax(zoom, linewidth=0.6)
ax.indicate_inset_zoom(zoom, edgecolor="#35414A", linewidth=0.65)
```

主图或 inset 使用不同投影时，先把小图覆盖边界转换到主图 CRS，再用线框和 `ConnectionPatch` 连接对应角点。影像对照保持同一拉伸或归一化，避免以配色差代替真实空间对比。渲染后检查连线、图例和边框均未遮盖数据或关键地物。
