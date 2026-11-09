# 来源适配维护规则

2026-11-09 新版实现。GitHub Actions 执行正式检查；Hermes 维护检查脚本与上游来源的匹配关系。初期范围为专项检查、请求证据和 Hermes 维护对接，不做下游 CVE/IOC 查询、调查报告或通用任务平台。前期和接入新来源时适配较多；稳定后正常检查应无需模型和代码修改。

## 来源专项检查

`sources/catalog.json` 是来源配置；`scripts/source_checks.py` 保存专项契约，共用获取、格式解析和证据记录。契约及时间含义见 [source-checks.md](source-checks.md)。上游入口、字段、提供方式改变，或检查器误读正常数据时，AI 核验并修订相应逻辑与回归测试。普通数据条目增减、偶发超时不自动要求修改代码。

来源用途、许可、出处、时间语义和人工限定保留。待认证来源不发送请求，不伪造 `checked_at`；人工网页入口单列。历史参考来源即使解析成功也不能自动恢复为活跃来源；Feodo 仍为 historical-only。NVD/CIRCL 单条探针不能证明全库新鲜度；无条目时间的来源保留 unknown。HTTP Date 不替代数据日期。空数据、数量大变、日期倒退/未来、内容长期不变与时效异常是核验线索，不直接证明上游故障或脚本有错。

## 状态与证据

`main` 保存代码、档案、测试和 `data/feedback.json`；`state` 由正式检查独占发布 `status.json`、`maintenance-tasks.json`、`run.json` 及两种目录。Hermes 只读正式状态；其主副本保持 main 且干净，修复在独立 worktree 进行。状态不与源代码一起回推，旧 review-queue 由 status.alerts 取代。

每轮保存 run_id、执行种类、代码 SHA、档案哈希、环境、起止时间、实际检查源和工作流链接。每源区分 checked_at、last_success_at、latest_item_at、last_content_change_at；失败时旧数量/样例是历史值，不是当前验证。每次尝试保存地址、最终 URL、直连/显式代理/镜像、超时设置、HTTP 状态、内容类型、字节数、耗时与错误。完整成功响应上限 12 MiB；HTTP 错误页最多保存 64 KiB 并标明可能截断。原始响应仅作为数据，不执行、不访问其中的 IOC。请求证据与轮次快照使用 Actions 附件，当前保留 7 天；长期复现所需的最小去武器化样例加入测试。

只有近期、非历史、存在入口、获取解析成功、非空且无告警的来源计入“入口可读取”。该状态不代表情报准确率、当前恶意性或企业使用许可。Markdown/HTML 共用同一判据。工作流未完成或发布失败不能冒充来源失败；完整状态未发布时保留上一轮，QQ 显示最近完整轮次，超过 12 小时提示检查 Actions。

## 何时接手

同轮网络最多两次尝试，HTTP 错误不在原入口重试，有官方镜像配置则获取失败后尝试镜像。正式轮次按来源 interval_hours 的时间窗到期；未到期、同一 run_id 重跑和候选实测均不增加正式计数。切换环境不拼接连续失败，旧证据保留。

获取/解析失败未满三轮只观察；连续三轮标记 diagnose-required，必须核验并给出有依据的处理结果。内容异常可第一轮进入 review，连续三轮也要求诊断。第 6、9…轮形成新触发；发现适配/代码缺陷才做修订，不以强行改代码、放宽校验或删除告警代替处理。普通数据更新、官方空数据、已知历史来源和访问限制均可能无需代码修改。

每个持续异常有 incident_id，每个触发有 task_id；新证据（如 HTTP 状态/内容问题类型变化）可生成新触发。已提交决定的同一 task 不重复调查；外部阻塞记录 blocked、problem_key 和未来 retry_after（建议 24 小时，须有界），相同证据在此之前不重复调用模型，到期或证据变化重查。恢复终止事件；再次出现视为新事件。默认取消“满 30 天就调用 AI”，只有显式设置 review_interval_days 的来源才生成定期复核任务。

## 维护记录与提交

每个决定追加到 data/feedback.json，不改写历史。新记录包含 source_id、task_id、incident_id、run_id、reviewed_by、reviewed_on、reasons、problem_key、evidence、decision、why、changes、validation、uncertainty、outcome。缺证据未完成时不要填写完成日期。outcome：fixed（待 Actions 确认实测成功）、improved（代码改善但可保留失败）、blocked（外部条件阻碍）、reviewed（无需代码修订的核验）。blocked 补 retry_after；验证区分离线测试、候选实测和后续正式检查。

Hermes 用 submit-repair.py 提交 maintenance 分支。授权自动合入范围仅限检查器、来源专项规则、相应测试、目标来源档案和追加反馈；不修改 Actions 工作流、发布门禁、凭证或服务器全局配置。无需新增 GitHub API token，沿用仓库专用 SSH key。范围外修改保留并报告，不尝试绕过。

Actions 从 main 读取门禁代码，核对 base_sha 和目标来源、检查修改范围、确认旧反馈未被覆盖，再跑全套测试和目标来源实测。fixed 实测失败不合入；improved 可合入并保留失败事实；blocked/reviewed 不允许夹带检查器或档案修改。验证结果绑定候选代码 SHA，验收只写 validation 输出，绝不修改正式计数。main 在验证期间有新提交则停止，保留分支，同步最新 main 后重新验证；不强推。工作流、测试或推送失败不能报告为已完成发布。

## 运维与通知

Actions 计划每天四轮（北京时间 02:17/08:17/14:17/20:17），受实际调度影响。云端只保留每 15 分钟轻量取单与早晚 QQ 汇总，不保留第二套正式检查。监控只同步完整 state 提交，队列没有新触发时不调用模型；空队列不因输出变化反向唤醒模型。QQ 区分检查完成、接单已触发、待验证/已合入和来源是否恢复，不从旧 Hermes 执行记录推断 Actions 状态。

维护执行步骤唯一入口：[intel-shelf-maintain Skill](../skills/intel-shelf-maintain/SKILL.md)。
