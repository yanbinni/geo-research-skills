---
name: litsearch
description: 多源英文学术文献检索工具（本地 CLI，零依赖）。也用于安装 litsearch 后的首次配置、换电脑和检查 API key。当你需要"找文献/列文献清单/做文献综述/检索论文/查某主题有哪些研究/找参考文献"时使用——包括"帮我找找这方面的论文""这个方向有什么经典文献""我需要一批文献自己下载""查一下 XX 的最新研究"等。Also use for English literature search, paper search, systematic review, literature review, bibliography building, citation snowballing, finding papers on a topic, "what has been published on X", "list references for me". 覆盖 OpenAlex、Crossref、DOAJ、CORE、arXiv、USGS、NASA NTRS、Google Scholar(SerpAPI/SearchApi)、OpenCitations、Unpaywall。触发词：文献检索、文献综述、找论文、列文献、查文献、参考文献、paper search、literature search、review。
---

# litsearch — 多源文献检索

一个跑在本机的零依赖 Python 工具，把 8 个免费文献源合并成一份去重清单，并**强制报告覆盖缺口**。

## 安装、换电脑或首次使用

从当前 `SKILL.md` 所在目录定位同级 `litsearch.py`，选择本机可用的 Python 3（Windows 可用 `py -3`，macOS/Linux 通常为 `python3`）。下文命令假定当前目录为技能目录，在项目目录工作时请用脚本绝对路径。

安装或配置任务先运行 `python litsearch.py doctor --offline`。根据本机状态，按 [新电脑配置指南](INSTALL.md) 引导用户选择数据源、在本地填写缺项并复查。普通检索在本机首次使用时也先做离线检查。用户选择跳过的数据源可在检索时排除并报告覆盖缺口。

## 什么时候该用它

✅ 用户要"找文献""列一批论文""做综述的检索部分""这个方向有什么研究""给我参考文献"
✅ 用户给了一个主题 / 一个 DOI / 一组关键词，想要成清单
✅ 需要判断某篇文章是否开放获取

❌ 用户要下载 PDF 全文 → 本工具只给链接和 OA 状态，不下载
❌ 要中文文献（知网/万方）→ 本工具没有，见"缺口"一节
❌ 要专利 / 标准 / 数据集 → 不在覆盖范围

## 标准工作流（照做，别跳步）

### 1. 拆英文关键词

把用户的中文问题拆成 **2–4 组英文概念块**，每组带同义词/缩写/传感器名/方法名：

```
"作物遥感分类" →
  concept1: crop, cropland, crop type, agriculture
  concept2: mapping, classification, identification
  concept3: Sentinel-2, Sentinel-1, Landsat, time series
  concept4: deep learning, CNN, transformer, machine learning
```

不要直接把中文机翻成一个长句丢进去——检索质量取决于关键词块。

### 2. 第一轮：期刊 + 预印本

```powershell
python litsearch.py search "<关键词>" --since 2018 --max 25 --limit-out 30 --abstracts 3
```

- `--since` / `--until` 控年份窗；综述通常取近 5–10 年，经典文献靠后面的引文雪球补
- `--max` 是每个源取多少（上限 100）；`--limit-out` 是最终输出多少
- `--abstracts N` 会额外打印前 N 篇摘要——**写综述时务必带上**，能直接判断相关性

### 3. 看"来源状态"再决定要不要补

输出里的 `## 来源状态` 表会告诉你哪个源挂了。**挂了就是挂了，不许假装完整。**

### 3.5 相关性分级（AI 判断，必做）

工具只做召回，**判断是你的活**。拿到合并后的 json，先出摘要速览再评：

```powershell
python litsearch.py digest --input review.json --top 60 --sort py
```

评完把结论写成**第二张清单**（规则见下）。

**分级标准（必须按这个来，不许自创）**

| 维度 | 取值 |
|---|---|
| 相关性 | **核心**（直接回答研究问题）/ **相关**（同一问题域，对象或方法不同）/ **边缘**（共享术语但问题不同）/ **无关** |
| 证据类型 | 综述 / 方法 / 案例 / 数据集 / 观点评论 |
| 建议动作 | **精读**（进正文）/ **快读**（读摘要图表即可）/ **略读**（只备份引用）/ **剔除** |

**进"高价值清单"的门槛**：相关性 ≥ 相关，**且**满足其一 —— 被引/年 ≥ 5、IF≈ ≥ 6、发表 ≤ 2 年且方法新颖。

**硬性要求**

- 每条理由必须**来自摘要里的具体内容**（"用了多城市 LST 对比，覆盖 30 个城市"），不许写空话（"该文很重要"）
- 摘要缺失的条目 → 标「无法判断」，并建议去原文或换源补摘要，**不许臆测内容**
- **一次最多评 60–80 条**；超出要分批，并明确写"已评估前 N 条，其余未评估"
- **不许静默丢弃任何条目**：完整清单照原样保留，你的判断只体现在第二张表里
- 必须补一栏"**未进清单但值得一看**"（3–5 篇），说明为什么——这是防止你漏掉的反向保险

### 3.6 相关性分级输出格式（照抄）

```markdown
## 清单一：按引用数排名（全量，工具生成）
| # | 年份 | 标题 | 期刊 | IF≈ | 被引 | 被引/年 | DOI | OA |

## 清单二：AI 判断的高价值文献（仅供参考）
| # | 相关性 | 证据类型 | 年份 | 标题 | 判断理由（来自摘要） | 建议 |

> ⚠️ 清单二由 AI 基于标题与摘要判断，**仅供参考**，不能替代你阅读原文；
> AI 未读全文，可能误判，尤其对方法细节和实验设计的把握有限。
> 判断依据（纳入/排除标准）：<把阶段 0 写的标准贴在这里>

### 未进清单但值得一看
| 标题 | 为什么可能有用 |
```

### 4. 第二轮：针对性补检

```powershell
# 只查灰色文献（政府报告、技术文档）
python litsearch.py search "<关键词>" --tier C --max 20

# 只查某个源
python litsearch.py search "<关键词>" --sources "usgs,ntrs" --max 20

# 按引用量排序找经典
python litsearch.py search "<关键词>" --sort cited --limit-out 20
```

### 5. 引文雪球（找综述"遗漏"的关键一步）

挑 1–3 篇最核心的文献，向前向后滚：

```powershell
python litsearch.py expand --doi 10.1016/j.rse.2021.112831 --max 30
```

- **后向**（它引用了谁）→ 找理论源头和经典方法
- **前向**（谁引用了它）→ 找最新进展和后续改进

### 6. 判定能不能免费下载

```powershell
python litsearch.py oa --doi "10.xxx/a,10.xxx/b"
```

或对一批 DOI：

```powershell
python litsearch.py oa --file dois.txt
```

### 7. 导出

```powershell
--format csv  --out result.csv     # 给 Excel
--format json --out result.json    # 给脚本/后续处理
--format md   --out review.md      # 直接是报告
```

## 输出规则（硬性）

**给用户的回答必须包含这四块，缺一不可：**

1. **文献清单表（清单 A）** — 按引用数排名的全量列表：序号、年份、标题、期刊、IF≈、被引、被引/年、DOI、OA
2. **高价值清单（清单 B）** — AI 基于摘要判断的相关性排序，**必须标注"仅供参考"**，格式见 3.6
3. **来源状态表** — 每个源成功/失败、条数、耗时
4. **"需要你自己补检的部分"表** — 工具自动生成，指向中文库、学位论文、灰色文献、新刊滞后等缺口

**红线：**

- ❌ 不许编造 DOI、标题、作者、年份——表里每一行都必须来自工具输出
- ❌ 不许因为某个源失败了就说"检索已完成"——必须说明缺了什么
- ❌ 不许把摘要改写成工具没返回的内容
- ❌ 清单 B 不许写成"这些就是最重要的"，只能写"按以下标准判断，这些相关性更高"
- ✅ 必须告诉用户"这份清单覆盖了什么、没覆盖什么"

## 命令速查

| 目的 | 命令 |
|---|---|
| 自检 | `litsearch.py doctor` |
| 看有哪些源 | `litsearch.py sources` |
| 主题检索 | `litsearch.py search "..." --since 2018 --max 25 --abstracts 3` |
| 只查灰色文献 | `litsearch.py search "..." --tier C` |
| 按引用排序 | `litsearch.py search "..." --sort cited` |
| 多组词合并 | `litsearch.py search "A" --format json --out a.json`（跑多组）→ `litsearch.py merge --input a.json,b.json` |
| 摘要速览 | `litsearch.py digest --input review.json --top 60 --sort py` |
| 引文雪球 | `litsearch.py expand --doi 10.xxx --max 30` |
| 开放获取判定 | `litsearch.py oa --doi "10.xxx,10.yyy"` |

## 结果里的三个影响力指标

| 列 | 含义 | 怎么用 |
|---|---|---|
| **被引** | OpenAlex 统计的总被引数 | 判断经典程度；注意新文章天生吃亏 |
| **被引/年** | 总被引 ÷ 发表年数 | **跨年份比较时用这个**，新文章不再吃亏 |
| **IF≈** | OpenAlex 的 2yr mean citedness，与影响因子同算法 | 判断期刊量级；5 以下一般，10 以上是好刊 |

⚠️ `IF≈` **不是** Clarivate JCR 官方影响因子，数值会有出入（通常略低），只能做量级比较。
需要在文中引用正式 IF 时，必须去 JCR 官网核对，不要直接引用这个数字。

**写综述时多轮检索是常态**：一个查询式最多每源 100 条，主题稍微复杂就要拆成 2–4 组
不同措辞分别查，再用 `merge` 合并。合并会自动去重。

## 覆盖边界（必须主动告知用户）

| 覆盖 | 不覆盖 |
|---|---|
| 英文期刊论文（OpenAlex/Crossref/DOAJ） | 中文文献（CNKI/万方/维普） |
| 英文预印本（arXiv） | 图书、标准、地图集 |
| 美国政府报告（USGS / NASA NTRS） | 专利 |
| 部分机构库/学位论文（CORE） | 商业数据库（Scopus/WoS）的受控词表检索 |
| 引文网络（OpenCitations） | 全文下载 |
| 开放获取状态（Unpaywall） | — |

本机配置路径、服务商入口和配额检查方法见 [新电脑配置指南](INSTALL.md)。

## 故障处理

| 现象 | 处理 |
|---|---|
| 所有源都 FAIL | 检查网络 / 梯子；跑 `doctor` |
| Google Scholar 失败 | 两家额度都满了，或 key 失效；换月或补 key |
| CORE 429 | 正常，匿名限流；等 1 小时或配 `core_api_key` |
| OpenAlex 429 | 额度用完，第二天重置；或减少 `--max` |
| 结果为空 | 关键词太窄，拆细一点；或放宽 `--since` |
| 中文报错乱码 | 先 `chcp 65001`，或改用 `--format json` |
