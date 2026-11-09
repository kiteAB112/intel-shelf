# 来源专项检查契约

每个已接入来源在 sources/catalog.json 选择同名 check_profile。通用请求/证据在 maintain.py，格式解析在 maintain.py 与 ioc_formats.py，来源语义契约在 source_checks.py。新增来源先确定契约与样例，再接入。

| 来源 | 专项检查 | 时间与限制 |
|---|---|---|
| NVD | vulnerabilities 列表、totalResults、每条 CVE ID、published/lastModified | 单记录探针，不判断全库新鲜度 |
| CISA KEV | catalogVersion、dateReleased、count 与列表长度、CVE ID 和 dateAdded | dateReleased 是目录发布日，dateAdded 是收录日；主入口获取失败可回退档案中的官方镜像 |
| Unit 42 | RSS/Atom 每条标题、HTTP(S) 引用、可解析的发布日期 | 研究报告发布时间，不等于攻击发生时间；30 天时效复核窗口 |
| Cisco Talos | 同上，独立 profile 与来源配置 | 报告发布时间；30 天窗口 |
| Check Point Research | 同上，独立 profile 与来源配置 | 报告发布时间；60 天窗口 |
| The DFIR Report | 同上，独立 profile 与来源配置 | 低频报告，180 天窗口 |
| OpenPhish | 每行合法 HTTP(S) URL，有主机名，拒绝 HTML | 无逐条观测时间；未知新鲜度，跨轮比较内容哈希 |
| TweetFeed | 无表头六列，指标类型/值、国际化域名、原帖引用域、可解析报告时间；无效指标隔离并统计 | reported_at 是社区报告时间，超过 5% 无效记录提示核验；native feed 范围 |
| C2IntelFeeds | 精确 CSV 表头 #ip,ioc，合法 IP、非空 C2 标签 | CSV 没有逐条时间，保留未知；仅非商业研究 |
| Feodo | JSON 数组、IP、整数端口、状态枚举、last_online 日期、家族与 first_seen | online 不表示当前在线；仍为历史参考，不纳入活跃来源 |

ThreatFox、URLhaus、MalwareBazaar 尚待认证接入，不伪造检查结果；Palo Alto PSIRT 是人工参考入口。

官方说明与发现出处保存在来源档案的 url、terms_url、discovered_via 等字段；来源核验决定保存在 data/feedback.json。契约变化须用对应失败样例复现，核对上游后修订，不因单次错误随意放宽规则。来源数据仅解析，不访问条目地址。
