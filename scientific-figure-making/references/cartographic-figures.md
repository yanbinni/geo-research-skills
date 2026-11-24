# Cartographic figures

Choose the layout for each panel according to what its position axes represent.

| Panel purpose | Layout |
|---|---|
| Show geographic locations, spatial patterns, or thematic values over a real study area | Use the cartographic layout below for raster and vector data. |
| Compare values, distributions, or trends | Use the original publication plotting style for bars, lines, scatterplots, and matrix heatmaps. A district name used as a category still belongs to a statistical plot. |
| Combine maps and statistical plots | Apply each layout to its own panels. Coordinate font, panel lettering, units, and spacing across the figure. |

Respect an example provided by the user as the layout reference. A data file's format alone does not determine the layout. For example, use a map for values located by longitude and latitude and a statistical plot for a citywide time series calculated from the same raster.

### Static cartographic layout

- Keep a closed frame around each rectangular map. Attach longitude and latitude labels to its edges, normally with longitude along the bottom and latitude along the left. Use light graticules below data and boundaries. On a projected map, use a geographic gridliner for degree labels or label the projected coordinate units. Match gridline and tick style across panels.
- Use the recorded coordinate reference system and explicit map extent. Align boundary overlays and data to a common CRS. Keep the study area at a consistent scale across comparable panels. Use a distance-based scale bar only when its calculation is appropriate for the displayed coordinates.
- Treat NoData and missing attributes separately from valid zero. Place legends and colorbars clear of the thematic layer. Use a sequential ramp for nonnegative magnitude, a diverging ramp where a meaningful reference such as zero separates two signs, and distinct colors for categories. Mark any display clipping on the colorbar. Preserve original values for statistics.
- For maps of the same variable across time or scenarios, use common color limits when the panels are intended for direct comparison. For different variables, label each colorbar with its own limits and units. At final size, check tick legibility, frame continuity, alignment, and colorbar placement.

### Raster thematic maps

- Read the GeoTIFF CRS, transform, bounds, and NoData. For a north-up rectilinear grid, either use masked data with imshow and georeferenced bounds or supply correctly ordered longitude and latitude coordinates to pcolormesh. Match the data row order to the selected renderer and verify orientation with a known location.
- A rotated or skewed grid needs affine-aware plotting or reprojection before plotting as a rectangle. Leave areas masked outside the study region visually distinct from a valid zero. When available, overlay the boundary in the same CRS to verify the map extent.

### Vector thematic maps

- Read geometries and their CRS, check the thematic field, and align layers before plotting. For polygons, use a continuous colorbar for quantitative values or a discrete legend for classes. Draw thin boundaries. Use an existing rate or an appropriate denominator when the map is meant to compare rates.
- Distinguish missing attributes with a neutral symbol or fill. For points, encode categories with explicit symbols and magnitudes with a size legend as appropriate. For lines, use color or width according to the variable. Render reference boundaries below point and line symbols when practical.
- In GeoPandas, plot the thematic layer on a shared axes, configure the legend and missing values, then fix the map bounds after plotting overlays. Use Cartopy gridlines when geographic ticks are needed for a projected map.

References: [GeoPandas mapping and plotting](https://geopandas.org/en/stable/docs/user_guide/mapping.html) · [Cartopy graticules and labels](https://cartopy.readthedocs.io/latest/matplotlib/gridliner.html)
