---
name: intel-shelf-investigate
description: 使用 intel-shelf 来源池调查公开 CVE 或恶意指标，解释命中、时间和证据范围。
---

从仓库根目录读取 workflows/investigate.md。按 sources/catalog.json 的用途、查询能力和使用条件选源，并结合 data/status.json 的检查日期及 data/feedback.json 的复核决定。

用 scripts/query.py 收集资料，按 templates/analysis.md 交付。沿原始公告或研究引用核实关键结论。区分源可读取、曾报告指标、近期观察到活动；分别给出处与日期。保留访问失败和未覆盖项。查询指标时只访问来源入口，不访问指标本身。
