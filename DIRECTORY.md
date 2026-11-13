# 来源目录

## 当前可读取的公开入口

已验证可读取 10 个；受限、异常及检查过期的来源单列在下方，不计入可用数量。

这是入口可用性验证，不是情报准确率认证或公司使用许可。RSS 用于发现文章，不是历史 CVE 搜索 API。时间为 UTC。

## 漏洞基础与已知利用

| 来源 | 用途 / 限制 | 获取 | 内容 | 新鲜度 | 检查时间 |
|---|---|---|---|---|---|
| [NVD](https://nvd.nist.gov/) · [数据入口](https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=1) | 漏洞记录与参考链接；单条探针只验证接口，不验证全库及时性 | 获取成功 | 基础解析通过 | 未知 | 2026-11-13T06:48:21.100617+00:00 |
| [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) · [数据入口](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json) | 已知利用漏洞及收录日期；未收录不代表未被利用；cisa.gov 直接入口在本执行环境返回 403（Akamai WAF 拦截），官方镜像见 mirror_endpoint | 获取成功 | 基础解析通过 | 复核窗口内 | 2026-11-13T06:48:21.100617+00:00 |
| [CIRCL Vulnerability-Lookup](https://vulnerability.circl.lu/) · [数据入口](https://vulnerability.circl.lu/api/vulnerability/CVE-2024-3400) | 按CVE查询跨来源记录、受影响产品和原始引用；可作NVD不可达时补充；维护探针只验证单条记录；转引CNA等数据，不是独立利用证据；不保证IOC/评论齐全 | 获取成功 | 基础解析通过 | 未知 | 2026-11-13T06:48:21.100617+00:00 |

## 攻击活动与研究报告

| 来源 | 用途 / 限制 | 获取 | 内容 | 新鲜度 | 检查时间 |
|---|---|---|---|---|---|
| [Unit 42](https://unit42.paloaltonetworks.com/) · [数据入口](https://unit42.paloaltonetworks.com/feed/) | 攻击活动、漏洞利用与 IOC 报告；按文章判断原始观测和引用关系 | 获取成功 | 基础解析通过 | 复核窗口内 | 2026-11-13T06:48:21.100617+00:00 |
| [Cisco Talos](https://blog.talosintelligence.com/) · [数据入口](https://blog.talosintelligence.com/rss/) | 威胁研究及事件响应报告；不保证每个 CVE 均有覆盖 | 获取成功 | 基础解析通过 | 复核窗口内 | 2026-11-13T06:48:21.100617+00:00 |
| [Check Point Research](https://research.checkpoint.com/) · [数据入口](https://research.checkpoint.com/feed/) | 恶意软件、活动与漏洞研究；报告发布时间不等于攻击发生时间 | 获取成功 | 基础解析通过 | 复核窗口内 | 2026-11-13T06:48:21.100617+00:00 |

## 入侵过程与狩猎线索

| 来源 | 用途 / 限制 | 获取 | 内容 | 新鲜度 | 检查时间 |
|---|---|---|---|---|---|
| [The DFIR Report](https://thedfirreport.com/) · [数据入口](https://thedfirreport.com/feed/) | 入侵过程、行为及检测线索；公开报告低频更新可正常；检测需适配日志 | 获取成功 | 基础解析通过 | 复核窗口内 | 2026-11-13T06:48:21.100617+00:00 |

## 恶意基础设施与载荷地址

| 来源 | 用途 / 限制 | 获取 | 内容 | 新鲜度 | 检查时间 |
|---|---|---|---|---|---|
| [TweetFeed](https://github.com/0xDanielLopez/TweetFeed) · [数据入口](https://raw.githubusercontent.com/0xDanielLopez/TweetFeed/master/week.csv) | 社区发布的 IP/域名/URL/MD5/SHA256；带发布者、报告时间和原帖引用；API 本地返回403；暂用官方发布的周度CSV；报告不等于恶意性验证，哈希情报不等同样本分析 | 获取成功 | 基础解析通过 | 复核窗口内 | 2026-11-13T06:48:21.100617+00:00 |
| [C2IntelFeeds（非商业研究）](https://github.com/drb-ra/C2IntelFeeds) · [数据入口](https://raw.githubusercontent.com/drb-ra/C2IntelFeeds/master/feeds/IPC2s-30day.csv) | 上游 verified 类别的30天C2 IP列表，附C2工具/指纹标签；CC BY-NC-SA 4.0；不可据此直接用于公司；本CSV无逐条时间或原始报告，指纹命中可能误报 | 获取成功 | 基础解析通过 | 未知 | 2026-11-13T06:48:21.100617+00:00 |

## 文件与恶意样本

| 来源 | 用途 / 限制 | 获取 | 内容 | 新鲜度 | 检查时间 |
|---|---|---|---|---|---|
| [TweetFeed](https://github.com/0xDanielLopez/TweetFeed) · [数据入口](https://raw.githubusercontent.com/0xDanielLopez/TweetFeed/master/week.csv) | 社区发布的 IP/域名/URL/MD5/SHA256；带发布者、报告时间和原帖引用；API 本地返回403；暂用官方发布的周度CSV；报告不等于恶意性验证，哈希情报不等同样本分析 | 获取成功 | 基础解析通过 | 复核窗口内 | 2026-11-13T06:48:21.100617+00:00 |

## 钓鱼

| 来源 | 用途 / 限制 | 获取 | 内容 | 新鲜度 | 检查时间 |
|---|---|---|---|---|---|
| [OpenPhish Community](https://www.openphish.com/phishing_feeds.html) · [数据入口](https://raw.githubusercontent.com/openphish/public_feed/refs/heads/main/feed.txt) | 有限覆盖的钓鱼 URL 集合；社区版标示 12 小时更新；无逐条观测时间；需核对条款 | 获取成功 | 基础解析通过 | 未知 | 2026-11-13T06:48:21.100617+00:00 |
| [TweetFeed](https://github.com/0xDanielLopez/TweetFeed) · [数据入口](https://raw.githubusercontent.com/0xDanielLopez/TweetFeed/master/week.csv) | 社区发布的 IP/域名/URL/MD5/SHA256；带发布者、报告时间和原帖引用；API 本地返回403；暂用官方发布的周度CSV；报告不等于恶意性验证，哈希情报不等同样本分析 | 获取成功 | 基础解析通过 | 复核窗口内 | 2026-11-13T06:48:21.100617+00:00 |

## 厂商安全公告

- [Palo Alto Networks PSIRT](https://security.paloaltonetworks.com/)：人工查阅入口。核对PAN-OS等产品影响版本、配置、修复与公告更正；仅适用于该厂商产品；不同分支修复必须读版本表；本入口不自动判断资产受影响

## 待接入或异常的来源（不计入可用）

历史参考来源也单列于此；人工网页入口列于对应类别。

| 来源 | 原因 | 最后成功获取 |
|---|---|---|
| [ThreatFox](https://threatfox.abuse.ch/api/) | 待认证/条件核验 | — |
| [URLhaus](https://urlhaus.abuse.ch/api/) | 待认证/条件核验 | — |
| [MalwareBazaar](https://bazaar.abuse.ch/api/) | 待认证/条件核验 | — |
| [Feodo Tracker（历史参考）](https://feodotracker.abuse.ch/blocklist/) | 仅历史参考；官方当前数据集状态见来源档案，未作为活跃情报接入 | 2026-11-13T06:48:21.100617+00:00 |

## 本次获取的内容示例

只展示来自 feed 的标题/引用，不访问这些链接；不代表已阅读或认可文章结论。

- NVD：CVE-1999-0095
- CISA KEV：Zoho ManageEngine Desktop Central File Upload Vulnerability
- Unit 42：[Attackers Use Autonomous AI to Target Semiconductor, Defense and Civil Society Sectors](https://unit42.paloaltonetworks.com/cairn-framework-ai-autonomous-attacks/)
- Cisco Talos：[Never be afraid to ask questions](https://blog.talosintelligence.com/never-be-afraid-to-ask-questions/)
- Check Point Research：[PHP2Shell Exploitation on Check Point Gateway](https://research.checkpoint.com/2026/php2shell-exploitation-on-check-point-gateway/)
- The DFIR Report：[BengalSEO Part 1: Anatomy of the Operation](https://thedfirreport.com/2026/08/24/bengalseo-part-1-anatomy-of-the-operation/)
- TweetFeed：`173[.]249[.]12[.]36`
- C2IntelFeeds（非商业研究）：`1[.]117[.]74[.]144`

## 恶意指标数据核验

| 来源 | 有效记录/去重指标/剔除条数 | 类型分布 | 时间含义与最新日期 | 原始引用条数 |
|---|---|---|---|---|
| TweetFeed | 778/744/0 | {'domain': 253, 'url': 338, 'ip': 73, 'sha256': 100, 'md5': 14} | report-time / 2026-11-12T16:44:48+00:00 | 778 |
| C2IntelFeeds（非商业研究） | 232/232/0 | {'ip': 232} | not-provided / 未知 | 0 |
| Feodo Tracker（历史参考） | 5/5/0 | {'ip': 5} | last-online / 2026-03-12T00:00:00+00:00 | 0 |

指标示例均去武器化；不生成封禁清单。上游 online 状态不代表本次已验证在线，报告时间也不等于指标仍有效。