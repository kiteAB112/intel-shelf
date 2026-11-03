# intel-shelf

一个本地优先的安全情报MVP：维护精选来源，按CVE或指标收集公开资料，再按统一规范形成有证据的调查结果。无大型平台、数据库或模型依赖；Python 3.9+，仅标准库。

## 从这里开始

- [浏览来源目录](index.html)。本地双击打开，可搜索和按类别筛选。每次维护同步生成页面；仅刷新现有数据的展示可运行 `python scripts/maintain.py --render-only`。

- [分类来源目录](DIRECTORY.md)：15个来源档案、7类；可读取入口、人工入口、待认证和历史来源分开。
- [CVE完整示例](examples/CVE-2024-3400.md)：自动资料收集后，由Codex完成公告、活动及排查核对。
- [指标查询示例](examples/indicator-lookup.md)：精确匹配与未匹配的解释。
- [调查流程](workflows/investigate.md)、[维护流程](workflows/maintain.md)：任何AI或人工都可执行。
- [MVP验收记录](docs/mvp-validation.md)：本轮真实运行、失败项及技术检查。

## 使用

在本项目根目录的PowerShell中执行。当前项目已创建.venv；新机器可用已安装的Python3运行 `python -m venv .venv`，不需要pip安装依赖。

```powershell
# 1. 维护来源（如网络需要代理则带--proxy；仅对本次请求生效）
.\.venv\Scripts\python.exe scripts\maintain.py --proxy http://127.0.0.1:7897
# 2. 查看CVE查询计划，不联网
.\.venv\Scripts\python.exe scripts\query.py CVE-2024-3400 --plan-only
# 3. 收集CVE公开资料；用途为狩猎
.\.venv\Scripts\python.exe scripts\query.py CVE-2024-3400 --purpose hunt --proxy http://127.0.0.1:7897
# 4. 查询公开指标；只下载来源数据，不访问这个指标
.\.venv\Scripts\python.exe scripts\query.py example.test --context company --proxy http://127.0.0.1:7897
# 5. 离线测试
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

支持输入CVE、IP（含IPv6）、域名、HTTP(S) URL、MD5、SHA256，接受常见去武器化写法。不接受带用户名/密码的URL；只提交公开查询对象，不输入内部资产、日志或凭证。

`--purpose triage`（默认初筛）或 `hunt`（狩猎）记录本次需求；`--context research`为默认研究场景，`company`排除已知非商业源，但不代表已完成所有来源的企业使用/再分发许可审核。

结果位于本地 `data/queries/<时间与对象摘要>/`：

- result.json：查询范围、每源结果、来源URL/获取时间/响应摘要和匹配记录。
- brief.md：自动资料包，区分找到记录、未匹配、失败、待接入和需人工查阅。
- analysis.md：按模板完成研判，不能把未填写的模板当成最终报告。

让AI读取workflows/investigate.md及这三个文件，即可接续公开公告、研究报告核对和结论编写。默认公开信息初筛；缺少资产上下文时，内部是否受影响保持未知。

## 已覆盖与边界

CVE可自动按编号查询NVD、KEV、CIRCL并输出引用；厂商公告、攻击活动、IOC与检测材料仍需AI/人工沿原始来源查证。研究博客只提供检索入口，不假装RSS覆盖全部历史。

指标可在已接入TweetFeed、OpenPhish及研究场景下的C2IntelFeeds中精确匹配，保留出处、报告时间和未知有效性。URL精确匹配不扩展域名/子域；未匹配只代表本次返回窗口无记录，不能判安全。Feodo历史来源不参与当前查询，认证未配置的来源明确跳过。

自动查询不使用模型；标准研判由执行任务的AI或人工完成。本地[Hermes适配试验](optional/hermes/README.md)已退出主流程，不再作为MVP验收前提。

## 维护与数据

当前优先维护来源池。AI 以 sources/catalog.json 选择来源，以 data/status.json 判断最近的技术检查结果，以 data/feedback.json 查阅有依据的历史决定。DIRECTORY.md 是阅读视图。维护者按 workflows/maintain.md 处理 data/maintenance-tasks.json 中的异常与到期复核。

maintain.py按每源间隔执行检查，可用 `--retry-failed`、`--force` 或 `--render-only`；未安装后台定时任务。检查观察、[人工反馈](data/feedback.json)与[来源档案](sources/catalog.json)分开。规则见[维护说明](docs/maintenance.md)，具体源取舍见[指标接入评审](docs/ioc-source-review.md)。

查询不访问IOC、不执行PoC、不下载样本、不扫描。普通维护不保存完整名单，保存少量去武器化示例；查询只保留匹配项与漏洞结构化事实，不镜像整份feed或文章。查询记录、运行历史、可选模型日志均Git忽略；对外分享先检查内容。所有网络请求只使用当前命令指定的代理，不修改持久设置。

目前完成的是来源维护和公开调查最小闭环，不承诺全网覆盖、生产级准确率或资产关联。云端调度见下方。

### 云端日常维护

云端 Hermes 在独立目录 ~/intel-shelf 工作。北京时间 08:17 运行 intel-shelf-check（无模型），08:47 运行 intel-shelf-review，对比来源 ID 和待办原因集合，变化才进入模型复核。交付位置为 Hermes 本机。云端记录、页面和修订保存在服务器，当前未配置 GitHub 同步。仓库中的 optional/hermes/cloud 保存两项任务使用的脚本。查运行情况可在服务器执行 `hermes cron list`，并查看项目中的 data/latest-check.log、data/status.json 和 data/maintenance-tasks.json。

