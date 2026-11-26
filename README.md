# codex-skills

面向地理、遥感与学术科研工作流的个人 Codex Skills 集合（涵盖英文多源文献检索与出版级地学科研制图）。

## 技能总览

| 技能 | 目录 | 定位 |
| --- | --- | --- |
| **litsearch** | [litsearch](litsearch/) | 多源英文学术文献检索、去重汇总与基于摘要的相关性分级 |
| **geo-scientific-figures** | [geo-scientific-figures](geo-scientific-figures/) | 地理、遥感与地球科学出版级 Python 静态制图（地图 + 统计 + 复合图） |

## 技能简介

### 1. [litsearch](litsearch/) — 多源英文学术文献检索

一个运行在本机的**零第三方依赖** Python 文献检索与整理工具，适用于做英文文献综述、查某研究方向代表性论文、整理参考文献清单以及核查论文开放获取（OA）状态。

- **多源聚合与去重**：内置 OpenAlex、Crossref、DOAJ、CORE、arXiv、USGS、NASA NTRS、Unpaywall 等免费源，并可选接入 Google Scholar（SerpApi / SearchApi）与 OpenCitations，自动去重合并。
- **诚实覆盖缺口报告**：每次检索均输出各数据源状态，明确标示失败或跳过的来源，不假装完整。
- **结构化检索与分级流**：支持将中文问题拆分为多组英文概念块检索、依据首轮题名与摘要补检合并，并按固定标准生成**全量清单 + AI 基于摘要筛选的高价值清单 + 反向漏检提醒**。
- **详细说明**：见 [litsearch/SKILL.md](litsearch/SKILL.md) 与 [配置指南](litsearch/INSTALL.md)。

### 2. [geo-scientific-figures](geo-scientific-figures/) — 地理与遥感科研制图

面向地理、遥感与地球科学研究的 Python / Matplotlib 出版级静态制图技能，覆盖专题地图、遥感影像可视化、精度验证与统计对比图以及地图＋统计复合图。

- **多场景 1:1 物理尺寸预设**：内置 `journal-en`（英文期刊单/1.5/双栏）、`thesis-cn`（中文毕设与大创 Word 版心、中英混排字体回退）、`slides`（组会/答辩 PPT）及 `custom`，论文图锁宽不锁死高，避免多余白边。
- **地理与遥感专业规范**：自带工具脚本 [geo_fig_kit.py](geo-scientific-figures/scripts/geo_fig_kit.py)，提供环境体检（`doctor`）与空间数据探测（`inspect`，支持 GeoTIFF / NetCDF / Shapefile / GPKG）；内置大栅格降采样、RGB 百分位拉伸、LULC 离散分类、中国审图合规底图红线、NoData 分级显示、感知均匀科学色表（禁用 `jet`/`rainbow`）以及默认平头色条＋真实截尾端 `≤`/`≥` 标注。
- **统计制图与套图一致性**：完整覆盖精度验证散点密度图（1:1 线、R²/RMSE/MAE/Bias）、分组柱状图、时空趋势带、混淆矩阵与复合排版；出图前先统筹整套图的风格与布局一致性，出图后执行 8 项 Visual QA 自检。
- **可复现随图脚本**：每次出图均在图件同目录保存可独立重跑的 `.py` 脚本，并在顶部集中标注中文可调参数区（字号、配色、范围、间距等），方便自行快速微调。
- **详细说明**：见 [geo-scientific-figures/SKILL.md](geo-scientific-figures/SKILL.md)。

## 快速安装

### 安装 `litsearch`

把下面这句话发给 Codex：

> 请从 https://github.com/yanbinni/codex-skills 的 `litsearch` 子目录安装技能。安装后请读取该目录的 INSTALL.md，运行离线检查，并引导我在本机配置所需的数据源。

具体字段、申请入口和验证命令见 [litsearch 配置指南](litsearch/INSTALL.md)。

### 安装 `geo-scientific-figures`

把下面这句话发给 Codex：

> 请从 https://github.com/yanbinni/codex-skills 的 `geo-scientific-figures` 子目录安装技能。安装后请运行 `python scripts/geo_fig_kit.py doctor` 检查本机 Python 地理依赖与中英文字体。

## 演进说明、致谢与许可

- **历史版本致谢**：本仓库早期曾包含一个基于 [ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers) 改写的科研制图技能备份（原 `scientific-figure-making`），特此向原作者致谢。现已针对地理与遥感领域全面独立重构为 [geo-scientific-figures](geo-scientific-figures/)，并已将旧版归档目录移除。
- **开源许可**：本仓库采用 [MIT License](LICENSE)。
