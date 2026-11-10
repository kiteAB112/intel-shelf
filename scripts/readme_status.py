"""Render a small README summary from a completed production observation."""
from datetime import datetime, timedelta, timezone
from html import escape
import re
from urllib.parse import urlsplit

from source_checks import display_status

START = '<!-- intel-shelf-status:start -->'
END = '<!-- intel-shelf-status:end -->'


def split_status(text):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('README must contain exactly one source status region')
    before, rest = text.split(START)
    body, after = rest.split(END)
    return before, body, after


def replace_status(text, body):
    before, _, after = split_status(text)
    return before + START + '\n' + body.rstrip() + '\n' + END + after


def cell(value):
    return escape(str(value)).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')


def date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def stamp(value):
    return date(value).strftime('%m-%d %H:%M') if value else '—'


def render(catalog, state, run, tasks, repository, timestamp):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Expected repository owner/name')
    base = 'https://github.com/' + repository
    statuses = {s['id']: display_status(s, state.get(s['id'], {}), timestamp) for s in catalog}
    integrated = [s for s in catalog if s.get('endpoint')]
    readable = sum(statuses[s['id']] == '入口可读取' for s in integrated)
    finished = date(run['finished_at'])
    lines = [f"最近完整检查：**{finished:%Y-%m-%d %H:%M} UTC** · "
             f"[运行记录]({base}/actions/runs/{run['run_id']}) · "
             f"代码 `{run['code_sha'][:7]}`",
             '', f"已接入 **{len(integrated)}** · 入口可读取 **{readable}** · 维护待办 **{len(tasks['tasks'])}**"]
    if timestamp - finished > timedelta(hours=12):
        lines += ['', '**检查结果已超过 12 小时，请查看工作流是否延迟或失败。**']
    lines += ['', '| 来源 | 类别 | 状态 | 最近检查 · UTC |', '|---|---|---|---|']
    for source in integrated:
        row = state.get(source['id'], {})
        label = statuses[source['id']]
        if label == '入口可读取' and row.get('freshness') == 'unknown':
            label += ' · 时效未知'
        url = source['url']
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username:
            raise ValueError('Invalid source reference URL')
        url = url.replace('(', '%28').replace(')', '%29').replace(' ', '%20')
        name = cell(source['name']).replace('[', '&#91;').replace(']', '&#93;')
        lines.append('| [' + name + '](' + url + ') | ' + cell(source['categories'][0])
                     + ' | ' + cell(label) + ' | ' + stamp(row.get('checked_at')) + ' |')
    excluded = [s for s in catalog if not s.get('endpoint')]
    if excluded:
        lines += ['', '<details>', '<summary>待接入 / 人工参考</summary>', '']
        for source in excluded:
            lines.append('- ' + cell(source['name']) + '：' + cell(statuses[source['id']]))
        lines += ['', '</details>']
    lines += ['', f'[完整目录]({base}/blob/state/DIRECTORY.md) · '
              f'[结构化状态]({base}/blob/state/status.json) · '
              f'[维护待办]({base}/blob/state/maintenance-tasks.json)']
    return '\n'.join(lines)
