---
name: intel-shelf-maintain
description: 处理 intel-shelf 的来源适配待办及每周全量脚本审阅，核验上游变化或检查器缺陷，按证据修订、验证并记录结果。
---

只维护 intel-shelf 来源与检查器的匹配关系。先读仓库 AGENTS.md、docs/maintenance.md；按目标来源阅读 docs/source-checks.md、档案和既有反馈，不读取私人知识库。

## 接单

云端主副本是 ~/intel-shelf，保持 main 且干净。先识别任务模式：普通接单按本节处理；提示词或预检输出标明 mode=weekly-audit 时执行下节全量审阅，不能因普通队列为空而结束。普通接单每小时轻量同步 GitHub 的完整轮次至 runtime/production/。读取 run.json、maintenance-tasks.json、对应 status.json 和 main 中 data/feedback.json；已处理 task_id 跳过，任务已恢复则结束。仅普通接单无待办时输出 [SILENT]。

读取目标源的每次请求证据、环境、入口、耗时、响应类型与解析结果；附件和工作流地址来自 run.json。若现有工具不能下载私有附件，先使用状态里的证据，再按官方入口做辅助请求并明确 hermes-cloud 环境；不能把辅助请求当成 Actions 实测成功。

diagnose-required 表示三轮后必须核验并给出处理结果，不意味着必须修改代码。区分上游改版、检查器缺陷、外部网络限制、正常数据变化、官方空数据和已知历史用途。有可复现的适配/代码问题才改；普通 review 可以仅记录核验。单项修复最多尝试两种有依据的方案，约 20 分钟内收敛；外部阻塞记录 blocked 和有界重查时间，不绕过审批或修改服务器设置。

## 每周全量审阅（weekly-audit）

北京时间每周日 10:30 执行，不使用“待办无变化跳过模型”的条件。intel-shelf-weekly.py 已同步正式观察、固定本次代码版本、建立只读用途的独立 checkout，并运行完整离线测试。预检输出给出 plan_path；先读该 plan.json 和测试日志，测试失败不能当作检查通过。预检成功本身不表示 AI 审阅完成。

按 plan.code_files 阅读全部检查器、来源解析/专项规则、接单/提交/验收脚本、Actions 工作流和测试，核对职责是否一致、异常和时间处理是否合理、是否存在静默漏检与测试缺口。按 plan.sources 逐一核对当前所有已接入来源的入口/提供方式、关键字段、日期语义、解析器和专项规则与近期 Actions 证据是否匹配；必要时核对官方说明/样例。四类 RSS 仍须逐源检查，不能只看一份通用代码就宣称四源均已核验。未接入或人工入口核对配置并单列，不能记为已实测。区分历史证据与当前请求，不能把旧代码产生的观察当作本次版本的实测。

将每个已接入来源、通用代码与测试的结论，以及证据版本、已检查/未完成项、问题和后续动作写入 plan.report_path，最后通过既有 QQ 会话交付周报。没有发现问题也要明确给出完整覆盖范围和结论，不输出 [SILENT]，不为凑周检强行修改代码。无法核验的来源或受运行时限限制的部分明确写未完成。

发现问题时先核对已有待办、反馈和维护分支，避免与日常维护重复修理。有依据的修复仍执行下节流程，使用 plan 中该源的 task 信息；不要在周检的固定 checkout 或云端 main 上修改。多个来源需分别、串行提交，前一项合入后再以最新 main 开始后一项。工作流/发布门禁等范围外问题记录并报告，不扩大自动合入权限。仅做周检且没有修订时，报告保存在运行端与 QQ，不为无问题的来源逐个制造 Git 提交。

## 修订与交付

每个任务建立独立工作副本，避免阻塞主副本的取单和汇报：

```sh
git fetch origin main
git worktree add -b maintenance/TASK_ID ../intel-shelf-maint-TASK_ID origin/main
```

在该副本中核对官方说明和实际样例，修改对应检查器/必要档案，补能捕获故障的回归测试。无需改代码也应追加可追溯决定。反馈字段与允许范围见 docs/maintenance.md；保留 task_id、incident_id、run_id 和 problem_key，旧反馈不可覆盖。

运行全套离线测试；需要本机辅助实测时：

```sh
INTEL_SHELF_ORIGIN=hermes-cloud python3 scripts/maintain.py --mode validation --source SOURCE_ID
```

候选实测不累计正式轮次。测试通过不代表来源恢复；不能删除告警、减少计数或无依据换源。blocked 补 retry_after（例如下一天同一时刻），若只是记录决定，outcome=reviewed。

提交前在反馈中区分离线验证、辅助请求与“Actions 尚待验证”，随后运行：

```sh
python3 ops/hermes/submit-repair.py --source SOURCE_ID --task TASK_ID --outcome fixed
```

outcome 按证据选 fixed/improved/blocked/reviewed。此命令只推 maintenance 分支，Actions 自动跑测试与目标实测；fixed 实测不通过不会合入，improved 可以保留失败。主分支变化会停止合入；保留候选分支，基于最新 main 合并自己的有效改动后重验，不强推、不覆盖他人改动。工作流/门禁/凭证等不在自动修改范围。

推送后核对结果；可用 git fetch origin main 与 git merge-base --is-ancestor CANDIDATE_SHA origin/main 判断是否已合入。工具无法确认 Actions 详情时报告“已提交，等待验证”，不能冒充修复完成。报告任务、根因、改动、测试与各环境实测、候选/正式提交和剩余未知；定时任务负责交付到已配置 QQ，无需另行发送消息。
