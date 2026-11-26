# 在这台电脑上配置 litsearch

安装前确认本机 Git 可访问仓库 `yanbinni/geo-research-skills`。技能位于仓库的 `litsearch` 子目录。安装后从实际安装位置找到与本文同目录的 `litsearch.py`。以下命令在该目录运行，使用本机的 Python 3 和标准库。Windows 可用 `py -3` 代替 `python`，macOS/Linux 可用 `python3`。

## 1. 检查已有配置

```sh
python litsearch.py doctor --offline
```

Codex 应先运行这个命令，再告诉用户这台电脑已配置哪些项、还可启用哪些数据源。离线检查只显示各字段的配置状态，不显示值，也不消耗查询配额。若提示 JSON 读取失败，先让用户在本机编辑器中修复现有文件。

## 2. 按需要启用数据源

仅使用 Crossref、arXiv、DOAJ、USGS 或 NASA NTRS 时可以直接检索。需要其他功能时，按下表填写相应字段。

| 功能 | 本机配置字段 | 对应环境变量 | 去哪里取值 |
|---|---|---|---|
| OpenAlex 检索与引文查询 | `openalex_api_key` | `OPENALEX_API_KEY` | 基础查询可匿名使用。经常检索时可登录账户，在 Settings → API key 复制密钥。[OpenAlex 认证说明](https://help.openalex.org/api/authentication/) |
| Google Scholar 首选服务 | `serpapi_api_key` | `SERPAPI_API_KEY` | 登录并复制个人 API key。[SerpApi 账户密钥](https://serpapi.com/manage-api-key) |
| Google Scholar 备用服务，也可单独使用 | `searchapi_api_key` | `SEARCHAPI_API_KEY` | 登录账户，在 Dashboard 复制 API key。[SearchApi](https://www.searchapi.io/) |
| CORE 机构库检索 | `core_api_key` | `CORE_API_KEY` | 可先尝试匿名查询，受限时填写个人访问密钥。[CORE API](https://core.ac.uk/services/api) |
| Unpaywall 开放获取查询 | `unpaywall_email` | `UNPAYWALL_EMAIL` | 填写自己的真实联系邮箱即可。[Unpaywall API](https://unpaywall.org/products/api) |
| 请求中的联系邮箱（可选） | `mailto` | `LITSEARCH_MAILTO` | 默认沿用 Unpaywall 邮箱。若只填本项，Unpaywall 查询也会使用它。 |

启用 Google Scholar 时两家服务任选一家。若两家都配置，工具先试 SerpApi，失败后再试 SearchApi。各账户的实际额度见服务商控制台。

## 3. 在本机填写

如果用户选择配置文件，由 Codex 运行：

```sh
python litsearch.py setup
```

命令会显示配置文件的实际位置，在首次运行时创建空白模板，已有文件会保留。默认位置为 Windows 的 `%USERPROFILE%\.litsearch\config.json` 或 macOS/Linux 的 `~/.litsearch/config.json`。已设置 `LITSEARCH_HOME` 的电脑使用该目录下的 `config.json`。

把实际文件路径给用户，让用户用本机文本编辑器打开，在相应字段的双引号之间填写并保存。其余字段可留空。密钥只在本机输入，不经聊天、命令行参数或 Git。若单位统一管理环境变量，可直接使用上表的变量并让 Codex 进程继承，跳过创建文件。非空配置文件字段优先于对应环境变量；更改用户级环境变量后，应重新启动 Codex 再检查。

## 4. 验证选中的服务

用户保存后，Codex 再运行 `python litsearch.py doctor --offline`，逐项核对用户选择的字段。若要验证联网检索，可只测试所选服务，例如：

```sh
python litsearch.py search "crop mapping" --sources google_scholar --max 1 --limit-out 1
python litsearch.py oa --doi 10.1038/nature12373
```

第一条会使用 Scholar 服务商的查询额度，第二条单独验证 Unpaywall 邮箱。需要检查全部八个检索源时运行 `python litsearch.py doctor`。查看每个源的 OK/FAIL 和错误原因；仅有离线结果时，报告“本机已配置，尚未联网验证”。用户跳过的可选服务不妨碍其他源。
