# Intel Shelf

一个由 GitHub Actions 定时检查、Hermes 辅助维护的威胁情报来源目录。

## 来源状态

<!-- intel-shelf-status:start -->
最近完整检查：**2026-11-10 01:33 UTC** · [运行记录](https://github.com/kiteAB112/intel-shelf/actions/runs/42736587720) · 代码 `73372c7`

已接入 **11** · 入口可读取 **10** · 维护待办 **0**

**检查结果已超过 12 小时，请查看工作流是否延迟或失败。**

| 来源 | 类别 | 状态 | 最近检查 · UTC |
|---|---|---|---|
| [NVD](https://nvd.nist.gov/) | 漏洞基础与已知利用 | 入口可读取 · 时效未知 | 11-10 01:33 |
| [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | 漏洞基础与已知利用 | 入口可读取 | 11-10 01:33 |
| [Unit 42](https://unit42.paloaltonetworks.com/) | 攻击活动与研究报告 | 入口可读取 | 11-10 01:33 |
| [Cisco Talos](https://blog.talosintelligence.com/) | 攻击活动与研究报告 | 入口可读取 | 11-10 01:33 |
| [Check Point Research](https://research.checkpoint.com/) | 攻击活动与研究报告 | 入口可读取 | 11-10 01:33 |
| [The DFIR Report](https://thedfirreport.com/) | 入侵过程与狩猎线索 | 入口可读取 | 11-10 01:33 |
| [OpenPhish Community](https://www.openphish.com/phishing_feeds.html) | 钓鱼 | 入口可读取 · 时效未知 | 11-10 01:33 |
| [TweetFeed](https://github.com/0xDanielLopez/TweetFeed) | 恶意基础设施与载荷地址 | 入口可读取 | 11-10 01:33 |
| [C2IntelFeeds（非商业研究）](https://github.com/drb-ra/C2IntelFeeds) | 恶意基础设施与载荷地址 | 入口可读取 · 时效未知 | 11-10 01:33 |
| [Feodo Tracker（历史参考）](https://feodotracker.abuse.ch/blocklist/) | 恶意基础设施与载荷地址 | 仅历史参考 | 11-10 01:33 |
| [CIRCL Vulnerability-Lookup](https://vulnerability.circl.lu/) | 漏洞基础与已知利用 | 入口可读取 · 时效未知 | 11-10 01:33 |

<details>
<summary>待接入 / 人工参考</summary>

- ThreatFox：待接入
- URLhaus：待接入
- MalwareBazaar：待接入
- Palo Alto Networks PSIRT：人工查阅

</details>

[完整目录](https://github.com/kiteAB112/intel-shelf/blob/state/DIRECTORY.md) · [结构化状态](https://github.com/kiteAB112/intel-shelf/blob/state/status.json) · [维护待办](https://github.com/kiteAB112/intel-shelf/blob/state/maintenance-tasks.json)
<!-- intel-shelf-status:end -->

状态表示入口与检查规则的匹配情况，不代表单条情报准确、指标仍然恶意或已获商业使用许可。NVD/CIRCL 使用单条探针；缺少条目时间的来源保留“时效未知”。

## 为什么做这个项目

在整理威胁情报来源和相关开源项目时，我注意到一个维护问题：数据源的接口、页面和提供方式会变化，而已有采集脚本有时还沿用旧的实现。即使定时任务仍在执行，也不一定能继续正确读取数据。

Intel Shelf 想尝试让 AI 参与这部分维护。常规请求、解析和状态检查交给 GitHub Actions；出现异常时，由 Hermes 根据请求证据、来源说明和现有代码判断原因。确实需要适配时，再修改脚本、补充测试，交回 Actions 验证。每周再进行一次完整审阅，检查现有规则是否仍然适用。

## AI 怎样参与

- **日常检查**：Actions 每天计划运行四轮，按各来源的 6/12/24 小时间隔请求，保存响应、解析结果和异常。
- **异常维护**：Hermes 每小时轻量取单；获取/解析连续失败三次必须诊断，内容异常可以提前复核。有依据才改脚本，正常运行无需调用模型。
- **每周审阅**：即使没有待办，也逐源核对入口、字段、时间语义和检查代码，报告覆盖范围与未完成项。
- **修改验收**：候选分支通过范围检查、全部测试和目标来源实测后发布；声称“已修复”必须实测成功。

`main` 保存代码、来源档案和维护记录；`state` 保存正式检查结果。README 仅自动更新上方状态区。项目聚焦来源检查与适配维护，可独立使用；不接入资产、扫描指标或执行样本。

## 使用

Python 3.9+，检查器只依赖标准库：

```sh
python -m unittest discover -s tests -q
python scripts/maintain.py --mode validation --source cisa-kev
```

本地结果写入忽略入库的 `runtime/`，不改变正式计数。Fork 后启用 Actions，并允许工作流写入仓库，即可运行检查；GitHub 定时触发可能延迟，以实际轮次为准。Hermes 是可选维护端，安装方式见 [Hermes 复用包](ops/hermes/README.md)。

[来源档案](sources/catalog.json) · [专项规则](docs/source-checks.md) · [维护规范与当前限制](docs/maintenance.md) · [维护 Skill](skills/intel-shelf-maintain/SKILL.md) · [维护记录](data/feedback.json)

## 许可

项目代码、原创文档和提示词采用 [MIT](LICENSE)。第三方来源数据仍适用其原有条款，详见 [NOTICE](NOTICE.md) 和各来源档案；本项目不打包再分发完整情报数据集。
