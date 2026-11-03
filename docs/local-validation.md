# 本地首轮验证

> 历史阶段记录。当前产品入口和验收以README及docs/mvp-validation.md为准；本页的数量、阶段和下一步描述保留为当时状态。

日期：2026-11-02。只查询公开 feed，不读取公司数据。没有安装后台任务、调用 Hermes 或推送远程。

- 六个公开入口获取与解析成功：CISA KEV、Unit 42、Cisco Talos、Check Point Research、The DFIR Report、OpenPhish。
- NVD 请求出现 TLS EOF，保留为获取失败；没有将其标为源永久失效。
- ThreatFox、URLhaus、MalwareBazaar 官方文档要求认证，暂未配置，未请求数据接口。
- Unit 42/Talos 初轮沙箱请求失败，沙箱外重试成功。当前状态描述本地执行环境；无法据此推断其他环境可用性。
- 新鲜度与格式成功分开：例如 OpenPhish 的纯 URL 列表不含观测日期，初轮 freshness 必须为 unknown。NVD 小探针不能评价全库更新延迟。
- 离线测试涵盖 HTML 登录页、空 feed、日期倒退/陈旧、数量突变、无日期、失败保留上次成功记录、连续失败、认证待定、检查间隔、恢复。

状态保留实际 UTC 时间，历史位于 data/history/。八项测试通过，未开展长期稳定性或内容质量验收。

来源发现参考：https://github.com/kraloveckey/threat-intelligence-feeds 与 https://github.com/Bert-JanP/Open-Source-Threat-Intel-Feeds 。认证和更新条款依据各来源官方文档入口（见 catalog）。检查结果不继承上游目录的红绿状态。

## 2026-11-03 纠正

上一版将待认证与当前可用混在同一主表，且只校验基础格式，展示不够准确。本轮分离可读取与未接入/失败项，增加 RSS 标题及文章引用示例、API 记录示例、检查过期判断、CISA 非标准小数时间解析回归验证；待认证不再更新请求时间。

复核中 NVD/DFIR 出现传输不稳定。增加有限网络重试后，本地七个公开入口获取并解析非空数据成功，三个认证来源仍未接入，不计入可用。保留历史故障及 request_attempts，不声称根因已修复或长期可靠。13 项离线测试通过；未变更来源地址、接入认证或推送远程。
