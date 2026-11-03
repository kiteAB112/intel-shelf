# Intel Shelf

Intel Shelf 自动维护一个精选威胁情报来源目录。每条来源档案说明它提供什么数据、从哪里获取、时间字段代表什么，以及使用时有哪些限制。

[按类别浏览来源](DIRECTORY.md) · [查看 JSON 档案](sources/catalog.json) · [查看复核决定](data/feedback.json)

## 来源怎样得到维护

1. **脚本检查入口。** 按每个源的更新频率请求数据，记录请求环境、地址、耗时和响应，再按预期格式解析内容。返回 200 的登录页也会触发解析异常。
2. **AI 复核变化。** 持续失败、内容异常或满 30 天到期的来源进入[维护待办](data/maintenance-tasks.json)。维护者核对官方说明、数据样例和时间含义，把证据与决定写入复核记录。例如，Feodo 的旧记录仍可读取，目录将其标为历史参考。
3. **把经验写回规则。** 确认上游格式变化后，用最小样例复现问题，修改解析器并增加离线测试。每轮维护从结构化数据重新生成分类目录和可在本地打开的[表格页面](index.html)。

[最近检查快照](data/status.json)记录技术观察。[维护规范](docs/maintenance.md)和[维护流程](workflows/maintain.md)说明如何判断异常、调整档案和验证修复。

## 本地使用

需要 Python 3.9 或更高版本，仅使用标准库。在仓库根目录运行：

```sh
python scripts/maintain.py                 # 检查到期来源并刷新目录
python scripts/maintain.py --retry-failed  # 提前重试失败来源
python scripts/maintain.py --render-only   # 使用已有快照重新生成目录与待办
python -m unittest discover -s tests       # 离线测试
```

## 定时运行与版本记录

云端 Hermes 每天北京时间 08:17 执行来源检查，08:47 检查待办集合的变化并按需启动 AI 复核。[调度脚本](optional/hermes/cloud)随仓库维护。云端结果保存在服务器，GitHub 展示最近一次提交的快照，页面上可查看生成时间。

来源档案、最新状态和待办、复核决定、生成的目录随 Git 保存。逐轮历史、请求日志、锁文件、凭证和本地运行环境留在运行端。
