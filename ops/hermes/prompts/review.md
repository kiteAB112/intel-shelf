执行当前项目 skills/intel-shelf-maintain/SKILL.md 的普通接单流程。

读取 runtime/production/ 中最新完整 Actions 轮次、来源状态和维护待办，结合 data/feedback.json 跳过已处理任务。没有未处理待办时输出 [SILENT]。

根据请求证据、官方说明和代码判断来源与检查器是否仍然匹配。有可复现依据才修改检查器或目标来源配置，并补回归测试。外部阻塞和无需修订的核验也要记录依据；不能为恢复绿灯而放宽规则。

在独立 worktree 中修订，用 ops/hermes/submit-repair.py 提交。区分本机辅助请求、Actions 候选实测、已合入和后续正式观察。无法确认验收时报告“等待验证”，不宣称来源已经恢复。由定时任务的投递配置交付结果。
