# 公开恶意指标来源接入评审

2026-11-03，Codex 本地执行，用户授权自主筛选及接入。不涉及推送、注册、付费、公司数据、样本下载或主动探测。

## TweetFeed：已接入公开周度 CSV

- 官方入口：https://github.com/0xDanielLopez/TweetFeed
- API https://api.tweetfeed.live/v1/today 在本机代理/直连均403，未绕过。选用官方发布渠道 https://raw.githubusercontent.com/0xDanielLopez/TweetFeed/master/week.csv ，本地实测成功；六小时间隔，不高频拉取仓库。
- 无表头六列：date,user,type,value,tags,tweet_url。保留首行、校验指标类型/值及原帖结构；域名支持IDNA。不合规指标剔除计数，超过5%触发异常；不访问指标或原帖。
- 本轮1006条：域名324、URL427、MD5 28、SHA256 104、IP 123；全部带原帖，最新报告时间2026-11-03 12:35:40 UTC。数量为本次快照，后续以status为准。
- 报告时间不是攻击发生或最近恶意行为时间，current_validity=unknown。标签不是归因结论，未核实所有原帖。可用于寻找线索/人工补查，不自动封禁。
- native feed CC0见官方README；external corroboration沿用上游条款，本次不接入该部分。多格式是同一来源，不算独立证据。

## C2IntelFeeds：非商业研究条件下可读取

- 官方入口：https://github.com/drb-ra/C2IntelFeeds
- feeds/IPC2s-30day.csv 本轮210条IP与工具/指纹标签。上游归为verified类，但本地没有独立验证C2。
- CSV无逐条时间、原始事件引用，30天窗口仅为上游说明，不能制造last_seen。新鲜度unknown；后续跨次摘要变化只能辅助复核。
- 许可CC BY-NC-SA 4.0：https://github.com/drb-ra/C2IntelFeeds/blob/master/License.md 。明确标为非商业研究，不直接用于公司或任意再分发。

## Feodo Tracker：读取成功，但近期用途不接受

- 官方说明：https://feodotracker.abuse.ch/blocklist/
- https://feodotracker.abuse.ch/downloads/ipblocklist.json 返回5条，最新last_online=2026-03-12；其中仍有status=online。11月获取成功不能证明3月指标仍在线。
- 自动标记review-freshness，移出近期可用清单，仅作历史观察。与说明页的近期窗口有差异，尚未查明，不推断整个项目停运。条款：https://abuse.ch/terms-of-use/ 。

## Blocklist.de：未收录

- 官方：https://www.blocklist.de/en/export.html ，按服务提供48小时攻击报告IP。
- SSH列表代理403、直连重置。本机未取得数据，不计为可用，也不宣判永久失效。

## 判断与实现

新增3个档案，总计13个唯一来源；TweetFeed跨基础设施、文件、钓鱼三类，不重复计总数。保存类型分布、去重数、引用数、时间含义和少量去武器化示例，不保存完整名单或生成封禁清单。

这是文档、数据结构和字段抽查，不是全量真实性、长期稳定性或公司使用条件验收。Hermes尚未执行本轮；后续应结合实际数据和本评审，不照抄上游目录绿灯。

## 后续更正（2026-11-03）

上述“Feodo仅需复核、Hermes尚未执行”属于早先阶段。后续Hermes真实网页调查发现Empty datasets横幅，Codex直接请求源站确认并沿FAQ核实官方当前称无活跃C2、数据集为空。因此Feodo已调整为historical-only，不再作为当前活跃源；旧JSON与说明差异仍未知，不宣判源停运。复核证据见 [来源维护决定](../data/feedback.json)。
