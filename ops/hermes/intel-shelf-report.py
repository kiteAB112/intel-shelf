"""Summarize the latest maintenance round for Hermes cron delivery."""
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

root = Path.home() / "intel-shelf"
cron = Path.home() / ".hermes/cron"
zone = timezone(timedelta(hours=8))
with sqlite3.connect(f"file:{cron / 'executions.db'}?mode=ro", uri=True) as db:
    db.row_factory = sqlite3.Row
    def latest(job):
        return db.execute("SELECT * FROM executions WHERE job_id=? ORDER BY claimed_at DESC LIMIT 1", (job,)).fetchone()
    check = latest("c3468924865d")
    review = latest("e206aebe6a47")

def stamp(value):
    return datetime.fromisoformat(value).astimezone(zone).strftime("%m-%d %H:%M") if value else "未知"

print("Intel Shelf 来源维护报告")
for label, row in (("来源检查", check), ("AI复核", review)):
    if row:
        print(f"{label}：{row['status']}，启动 {stamp(row['started_at'] or row['claimed_at'])}，结束 {stamp(row['finished_at'])}")
    else:
        print(f"{label}：暂无执行记录")
if check and review and review["claimed_at"] < check["claimed_at"]:
    print("本轮AI复核尚无运行记录，以上为上一轮结果。")
state = json.loads((root / "data/status.json").read_text())
tasks = json.loads((root / "data/maintenance-tasks.json").read_text())["tasks"]
print(f"来源档案 {len(state)} 个，当前AI待办 {len(tasks)} 项。")
for sid, row in state.items():
    if row.get("alerts"):
        attempts = row.get("request_attempts", [])
        elapsed = " / ".join(str(a["elapsed_ms"]) + "ms" for a in attempts if "elapsed_ms" in a)
        status = row.get("http_status", "未知")
        print(f"- {sid}：{', '.join(row['alerts'])}；HTTP {status}；耗时 {elapsed or '未记录'}；检查于 {stamp(row.get('checked_at'))}")
for task in tasks:
    print(f"待办 {task['source_id']}：{', '.join(task['reasons'])}")
if review:
    output_dir = cron / "output" / review["job_id"]
    outputs = sorted(output_dir.glob("*.md"))
    if outputs:
        text = outputs[-1].read_text()
        response = text.split("## Response\n", 1)[-1].strip() if "## Response\n" in text else ""
        if response == "[SILENT]":
            print("AI复核无新增报告。")
        elif response:
            print("AI结果摘要：" + response[:1100])
        elif 'no_change (agent run suppressed)' in text:
            print('AI复核：待办触发条件无变化，本轮未调用模型。')
        else:
            print("AI输出未包含结果正文，请查运行记录。")

feedback = json.loads((root / 'data/feedback.json').read_text())
for item in feedback:
    verified_today = item.get('verified_at') and datetime.fromisoformat(item['verified_at']).astimezone(zone).date() == datetime.now(zone).date()
    if item.get('changes') and (item.get('reviewed_on') == datetime.now(zone).date().isoformat() or verified_today):
        print(f"维护变更 {item['source_id']}：{item.get('outcome', '未知')}")
        print('改动：' + '；'.join(item['changes']))
        print('依据：' + item.get('why', '未记录'))
        print('验证：' + str(item.get('validation', '未记录')))
def git(*args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=25).strip()
try:
    head = git("rev-parse", "HEAD")
    remote = git("ls-remote", "origin", "refs/heads/main").split()[0]
    dirty = bool(git("status", "--porcelain"))
    print(f"GitHub：{'已同步' if head == remote and not dirty else '存在待同步改动或分支差异'}，云端提交 {head[:7]}。")
except (subprocess.SubprocessError, IndexError) as exc:
    print(f"GitHub同步状态核验失败：{type(exc).__name__}")
print("仓库 https://github.com/kiteAB112/intel-shelf")
