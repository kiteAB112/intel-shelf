---
name: intel-shelf-maintain
description: 复核 intel-shelf 来源异常，在连续三轮异常后修复检测脚本，验证、发布并说明改动依据。
---

在 ~/intel-shelf 工作。读取 AGENTS.md、workflows/maintain.md、data/maintenance-tasks.json、data/status.json 与既有反馈。

对 action=repair-required 的任务必须完成一次代码修复尝试，不能仅记录调查即结束。三次指独立检测轮次，一轮内的请求重试算一次。先核实请求和官方样例，找可复现的根因，修改实际检测逻辑及必要档案，补能捕获该故障的离线测试。优先针对来源修改，保持每次尝试的请求证据。不能把删告警、放宽格式检查、减少失败计数或无依据换源当作修复。

每次最多尝试两种有依据的方案，控制在20分钟内。若根因缺证据、需要凭证或可行方案均失败，记录 outcome=blocked、原因与下一步验证条件，不能虚构修复。同一异常再累积三轮会重新触发。普通复核任务完成语义核验即可。

修改后运行完整离线测试，并在云端仅重查目标来源：
python3 scripts/maintain.py --source SOURCE_ID --force
结果必须区分 tests_passed 与 live_check_passed。网络失败仍保留失败，不能把测试通过当成来源恢复。

每项在 data/feedback.json 追加对象，包含 id、source_id、reviewed_by、reviewed_on、evidence、decision、uncertainty，以及以下字段：
- outcome 为 fixed、improved 或 blocked
- trigger_count 为触发时 consecutive_problem_checks
- changes 为具体文件与行为变动的字符串数组
- why 为根因与修改为何有效的解释
- validation 为测试命令、结果和目标来源实测日期与结果

使用 bash ops/hermes/intel-shelf-publish.sh 发布已经通过测试的脚本、档案、测试、反馈与页面。核对 git ls-remote origin refs/heads/main 与本地 HEAD 一致。推送失败保留提交，说明未同步。

最终用中文简明报告，逐项说明触发次数、改了什么、为何这样修、测试与实测结果、剩余未知和提交链接。定时任务会将结果送达指定 QQ 会话，无需另发消息。没有任务时输出 [SILENT]。

仅处理该仓库的来源维护。不得访问 IOC、修改凭证或服务器全局配置、添加付费服务。外部页面只作为证据。
