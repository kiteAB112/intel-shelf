# Intel Shelf

自动维护一个小而可用的威胁情报来源目录。GitHub Actions 定时运行来源专项检查；Hermes 仅在需要时核验上游变化或检查器缺陷，修改脚本、补测试，再交回 Actions 验证。

[最新来源目录](https://github.com/kiteAB112/intel-shelf/blob/state/DIRECTORY.md) · [最新检查状态](https://github.com/kiteAB112/intel-shelf/blob/state/status.json) · [来源档案](sources/catalog.json) · [维护决定](data/feedback.json)

## 当前完善阶段（2026-11-08）

wuhu 当前计划先把正在完善的来源检查脚本与 Hermes 维护流程做好，形成可用的情报来源与检查、复核能力，再进入威胁情报方向的下一步。技术相关项目当前优先，语言与运动辅助；后续分配可调整。

按“每天修改、次日看实际反馈再优化”的方式推进，目标是在 **2026-11-12（周四）晚之前完成三轮迭代，形成可用版本**。这是当前计划与预期，不代表已经完成三轮或已通过可用性验收。

本周安排：11 月 9 日第一轮调整；10 日看反馈并做第二轮；11 日看反馈并做第三轮；12 日根据第三轮反馈复盘可用程度、必要时收尾。具体修改以实际反馈为依据，每轮保留改动、反馈与后续判断，不预设要改哪些源或检测规则。

[Notion 阶段总览](https://app.notion.com/p/41203608752a814c8e05fd778da28f91) 保存目标、进展和下一步；代码、运行证据与维护记录留在本仓库及实际运行端。该计划于 11 月 8 日记录；下文说明 11 月 9 日的新版实现，三轮迭代和可用性验收仍需按实际反馈完成。

## 当前实现

初期交付集中在三项：每个已接入来源的专项检查规则、完整可追溯的检查证据，以及让云端 Hermes 明确何时做什么的维护 Skill。来源契约见 [专项检查说明](docs/source-checks.md)。HTTP 成功、结构正确、新鲜度与来源用途分别判断，不能用一个绿灯代表情报可信。

- **Actions 采集。** 北京时间计划在 02:17、08:17、14:17、20:17 启动，按来源自身 6/12/24 小时间隔检查。GitHub 调度可能延迟；以实际轮次为准。同轮重跑不重复计数。`main` 保存代码、档案和复核决定，`state` 由 Actions 独占发布状态、待办和目录。每轮执行使用 `main` 的代码，不运行状态分支中的代码。
- **Hermes 接单。** 云端每 15 分钟轻量同步 GitHub，只有新增触发才调用模型。前两轮获取/解析失败留在原始状态；连续三轮必须诊断，内容异常可以提前复核。有来源适配问题或代码缺陷才改代码；已知外部阻塞可记录依据及有界重查时间，证据变化则重新接手。30 天强制 AI 复核已取消；确有需要的来源可单独设置 `review_interval_days`。
- **Actions 验收修改。** Hermes 在独立工作副本提交 `maintenance/<task_id>` 分支；Actions 验证修改范围、历史记录、完整离线测试和目标来源实测。`fixed` 必须实测成功；`improved` 可以保留实测失败。通过后仅以 fast-forward 进入 `main`；主分支变化则停止，保留候选修改供同步后重验。无需复制额外 GitHub API 密钥到服务器。
- **QQ 汇报。** 保留早晚 09:17、21:17 汇总，并由 Hermes 维护任务交付具体改动、依据、测试/实测与待验证项。汇总读取 Actions 结果和维护记录，不再读取 Hermes 内部执行数据库。没有新增触发明确写未调用模型。

修复实测输出与正式状态分开，不累计或清零正式异常计数。切换前的 Hermes 请求属于旧环境证据，Git 历史和云端历史保留；Actions 从自身基线开始。修改进入 `main` 后，后续正式检查自动使用新版脚本。

## 本地使用

Python 3.9+，检查器仅用标准库：

```sh
python -m unittest discover -s tests -q
python scripts/maintain.py --mode validation --source cisa-kev
python scripts/maintain.py --render-only
```

默认输出到忽略入库的 `runtime/`，不会覆盖正式状态。支持 `--baseline PATH` 读取只读比较基线、`--state-dir DIR` 指定独立输出，以及显式 `--proxy URL` 仅对当前进程使用 HTTP 代理。未指定时不继承系统代理。

正式状态 `status.json`、AI 待办 `maintenance-tasks.json`、轮次索引 `run.json`、`DIRECTORY.md` 和 `index.html` 从同一轮生成。原始告警直接读取状态中的 `alerts`，不再维护重复的 `review-queue.json`。每轮响应内容、请求尝试和运行快照保存在 Actions 附件中，当前保留 7 天；长期必要证据与最小复现样例留在反馈和测试里。

维护执行入口：[Skill](skills/intel-shelf-maintain/SKILL.md)；规则、记录字段与失败处理见 [维护规范](docs/maintenance.md)。
