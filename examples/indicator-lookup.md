# 指标查询示例：命中和未命中并存

2026-11-03，Codex使用已公开报告的去武器化URL运行：

```powershell
.\.venv\Scripts\python.exe scripts\query.py 'hxxp://181[.]85[.]173[.]171:8001/api/blob' --purpose hunt --context company --proxy http://127.0.0.1:7897
```

本地资料包：data/queries/20261103T135848087482Z-245562b7/（Git忽略）。只下载已登记的TweetFeed周度CSV与OpenPhish列表，从未访问该URL。

- TweetFeed：精确匹配1条，保留发布者、报告时间和原帖引用，current_validity=unknown。
- OpenPhish：本次列表未匹配。它覆盖钓鱼URL，不是所有恶意URL，不能因此推翻TweetFeed线索或判该地址安全。
- ThreatFox、URLhaus：认证未配置，明确跳过；没有伪造API结果。

可得结论：该URL曾被社区收录报告，需阅读result.json中的原帖核对角色与上下文。尚未阅读原帖并独立确认真实性，不将命中升级为当前恶意判定、具体CVE利用或活动归因，不自动封禁。公司场景过滤器只排除已知非商业限制，不代替完整许可审核。

这是一次公开指标匹配验收，未用公司日志、未核查内部访问或感染。后续有实际告警时，应另行确认方向、时间、命中设备与关联行为。
