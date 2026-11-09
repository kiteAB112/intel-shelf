# 来源适配维护入口

当前职责：GitHub Actions 定时运行来源专项检查；Hermes 在异常触发时核验上游与检查器的适配关系，并将有依据的修订交给 Actions 验收。

- 执行步骤：[维护 Skill](../skills/intel-shelf-maintain/SKILL.md)。
- 计数、状态、记录字段、权限与验证要求：[维护规范](../docs/maintenance.md)。
- 各来源契约与时间含义：[专项检查说明](../docs/source-checks.md)。
- 正式观察、维护待办、轮次索引与目录在 GitHub state 分支；云端只读副本位于 runtime/production/。

此入口替代旧版“云端正式检查并直接发布全部文件”的执行流程。
