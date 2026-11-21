# Intel Shelf 检查结果

`state` 保存 GitHub Actions 最近发布的正式检查结果。[主分支](https://github.com/kiteAB112/intel-shelf/tree/main)保存代码、来源档案和维护记录。两个分支分别提交，GitHub 上的 ahead / behind 数字反映各自的提交历史。

| 文件 | 存放内容 |
| --- | --- |
| [DIRECTORY.md](DIRECTORY.md) | 给人看的 Markdown 目录。按类别列出来源、入口、用途、限制及最近一次检查的结果。用途和限制来自来源档案。 |
| [index.html](index.html) | 可在浏览器打开的静态结果页，展示来源状态、异常与维护信息。 |
| [run.json](run.json) | 本轮检查清单。包含轮次编号、起止时间、执行时的代码提交、实际检查的来源和 Actions 链接。只检查到期来源，轮次时间可能与某个来源的检查时间不同。 |
| [status.json](status.json) | 按来源保存的最近观测。包含检查时间、获取和内容校验结果、条目数、时效、异常及请求证据摘要。请求记录中的 `body_file` 指向对应 Actions 附件内的文件。 |
| [maintenance-tasks.json](maintenance-tasks.json) | 本轮发布的维护待办。每条包含来源、任务号、触发原因及关联轮次，Hermes 据此取单。`"tasks": []` 表示这份快照没有待办。 |

## 查一轮结果

1. 从 [run.json](run.json) 的 `workflow_url` 打开 Actions 运行记录，确认本轮检查了哪些来源。
2. 在 [status.json](status.json) 按来源编号核对 `checked_at` 和异常。要看当时的响应内容，从关联的 Actions 轮次下载检查附件，附件保留 7 天。
3. 用 `task_id` 在 [维护记录](https://github.com/kiteAB112/intel-shelf/blob/main/data/feedback.json)查诊断、修订和验收结果。旧待办可从 [state 提交历史](https://github.com/kiteAB112/intel-shelf/commits/state/)回查。

GitHub 文件列表显示的是该文件最后一次发生改动的时间。待办一直为空时，`maintenance-tasks.json` 的时间可能早于最新轮次。来源显示「入口可读取」，表示当次响应符合现有检查规则。时效和使用范围要以各来源记录为准。更多细节见[维护规范](https://github.com/kiteAB112/intel-shelf/blob/main/docs/maintenance.md)。
