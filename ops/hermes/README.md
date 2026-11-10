# Hermes 维护端

可选组件：Actions 独立完成正式检查；Hermes 读取异常、适配脚本和每周审阅。此目录提供代码、提示词和脱敏部署蓝图，不包含运行端的真实任务数据库、会话目标、模型凭证或 SSH key。

## 文件

| 文件 | 用途 |
|---|---|
| [维护 Skill](../../skills/intel-shelf-maintain/SKILL.md) | 调查、修订、证据、验证和交付规则 |
| [日常 Prompt](prompts/review.md) / [周检 Prompt](prompts/weekly-audit.md) | 选择任务模式和输入；详细规则以 Skill 为准 |
| [任务蓝图](jobs.example.json) | 小时取单、每周审阅及早晚纯脚本汇报 |
| `intel-shelf-watch.py` | 同步完整 state，输出稳定的待办编号供 monitor 比较 |
| `intel-shelf-weekly.py` | 固定代码版本、跑测试、准备完整审阅清单 |
| `submit-repair.py` | 测试并提交授权范围内的维护候选 |
| `intel-shelf-report.py` | 从正式观察和反馈生成汇报，不调用模型 |
| [反馈样例](examples/feedback.json) | 虚构示例，不可当作实际维护证据 |

## 准备

在已安装 Hermes 的运行端克隆自己的仓库或 fork，并保持项目主副本在干净的 `main`。先手动运行一次 Actions，确认已有 `state`。Python 3.9+；Hermes 版本需要支持 `--monitor-script`、`--workdir`、`--timezone` 和 script + Skill 任务组合，可先查看 `hermes cron create --help`。

项目沿用 Git 的已配置仓库访问方式，不在包里提供凭证。只查看状态需要读权限；自动提交维护分支需要写权限。仓库写权限并不天然限制只能推某个分支，Skill/验收门禁是流程约束；自动维护前由部署者核对仓库规则和权限。模型、网络和通知接收方在 Hermes 本地配置。

## 安装 Skill 与入口

在项目根目录执行；默认使用 `$HERMES_HOME`，未设置时使用 `~/.hermes`：

```sh
python3 ops/hermes/install.py --dry-run
python3 ops/hermes/install.py
```

安装器只复制 Skill 并生成三个调用仓库脚本的薄入口，不创建定时任务、不修改凭证。已有不同内容时停止，检查后可用 `--force` 更新；代码拉取后入口直接运行新版脚本，Skill 文本更新则重新运行安装器。自定义 profile 可传 `--hermes-home /path/to/profile`，创建任务时使用同一 profile。

## 创建任务

下列命令是 Bash 示例，在项目根目录执行。Prompt 直接读取本仓库文件；安装位置和投递目标由部署者确定。示例投递到本地，不绑定 QQ 或任何真实会话。

```sh
hermes cron create '47 * * * *' "$(cat ops/hermes/prompts/review.md)" \
  --name intel-shelf-review --timezone Asia/Shanghai --workdir "$PWD" \
  --monitor-script intel-shelf-watch.py --skill intel-shelf-maintain --deliver local

hermes cron create '30 10 * * 0' "$(cat ops/hermes/prompts/weekly-audit.md)" \
  --name intel-shelf-weekly-audit --timezone Asia/Shanghai --workdir "$PWD" \
  --script intel-shelf-weekly.py --skill intel-shelf-maintain --deliver local

hermes cron create '17 9,21 * * *' \
  --name intel-shelf-report --timezone Asia/Shanghai --workdir "$PWD" \
  --script intel-shelf-report.py --no-agent --deliver local
```

先用 `hermes cron list` 确认是否已有同名任务，避免重复创建。`jobs.example.json` 是部署蓝图，`prompt_file` 表示需读取的本项目文件，不是 Hermes 原生导入字段；不要用它覆盖真实 `cron/jobs.json`。已有任务更新方式以当前版本 CLI 为准。通知按 [Hermes 官方调度文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) 配置，真实平台 ID 和 token 留在运行端。

## 运行与确认

小时取单没有新增待办时不需要模型；周检不使用这个跳过条件。取单只自动同步三个 JSON 索引，原始响应留在 Actions 附件；AI 按证据链接获取，工具无法访问时应明确缺项或辅助请求环境。

周检产物保存在运行端 `runtime/weekly/`：`plan.json`、测试日志、正式观察快照和 AI 的 `report.md`。生成计划或通过测试，不等于完成 AI 审阅。维护候选提交后必须核对 Actions 结果；正式计数由后续 Actions 轮次更新。

当前验收状态及已知限制见 [维护规范](../../docs/maintenance.md)。安装本包并不保证来源永远可用，也不保证 AI 总能独立修复。
