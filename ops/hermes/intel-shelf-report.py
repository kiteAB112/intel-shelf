"""Report Actions observations and maintenance decisions for QQ delivery."""
import importlib.util
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('watch', Path(__file__).with_name('intel-shelf-watch.py'))
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


def main():
    data = watch.sync()
    run, state = data['run.json'], data['status.json']
    tasks = data['maintenance-tasks.json']['tasks']
    zone = timezone(timedelta(hours=8))
    stamp = datetime.fromisoformat(run['finished_at']).astimezone(zone)
    print('Intel Shelf 来源适配维护报告')
    print(f"最近完整检查：{stamp:%m-%d %H:%M}，GitHub Actions 轮次 {run['run_id']}，代码 {run['code_sha'][:7]}")
    elapsed = datetime.fromisoformat(run['finished_at']) - datetime.fromisoformat(run['started_at'])
    print(f"本轮实际检查 {len(run['checked_sources'])} 个来源，耗时 {elapsed.total_seconds():.1f}s。")
    if datetime.now(timezone.utc) - datetime.fromisoformat(run['finished_at']) > timedelta(hours=12):
        print('最近完整检查已超过12小时；后续工作流是否失败或未执行，请查看 Actions。')
    feedback = json.loads((ROOT / 'data/feedback.json').read_text(encoding='utf-8'))
    handled = {r.get('task_id') for r in feedback if r.get('task_id')}
    pending = [t for t in tasks if t['task_id'] not in handled]
    print(f'来源档案 {len(state)} 个，当前未处理维护待办 {len(pending)} 项。')
    monitor_path = ROOT / 'runtime' / 'monitor-status.json'
    monitor = json.loads(monitor_path.read_text(encoding='utf-8')) if monitor_path.exists() else {}
    if monitor.get('run_id') == run['run_id']:
        print('本轮接单监控：已触发 AI，处理进度见维护记录。' if monitor.get('model_requested') else '本轮接单监控：待办无新增触发，未调用模型。')
    else:
        print('本轮接单监控尚无记录，暂不判断模型是否被调用。')
    for sid, row in state.items():
        if row.get('alerts'):
            print(f"- {sid}：{', '.join(row['alerts'])}；{row.get('error', '需结合来源语义判断')}；连续失败 {row.get('consecutive_failures', 0)} 轮")
    for item in feedback:
        if item.get('task_id') and item.get('reviewed_on') == datetime.now(zone).date().isoformat():
            print(f"维护 {item['source_id']}：{item.get('outcome')}；{item.get('decision')}")
            print('改动与依据：' + str(item.get('changes', [])) + '；' + item.get('why', ''))
            print('验证：' + str(item.get('validation', '未记录')))
            print('Actions 验证：' + str(item.get('actions_validation', '尚未记录')))
    print('正式状态已从 GitHub state 分支读取；修复仅在 Actions 验证后进入 main。')
    print(run.get('workflow_url') or '暂无正式工作流链接；请检查 run.json。')


if __name__ == '__main__':
    main()
