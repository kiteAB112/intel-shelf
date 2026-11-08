"""Public source checks; Python 3.9+, standard library only. Never visits feed items."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from time import monotonic
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ioc_formats import summary as ioc_summary
from directory_page import page

IOC_FORMATS = ('tweetfeed-csv', 'feodo-json', 'c2-csv', 'ip-list')

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc)


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(value)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def parse_date(value):
    if not value:
        return None
    try:
        value = value.replace('Z', '+00:00')
        # Python 3.9 accepts 3/6-digit fractions, while publishers may emit others.
        import re
        value = re.sub(r'\.(\d+)(?=[+-]\d{2}:\d{2}$)', lambda x: '.' + (x.group(1) + '000000')[:6], value)
        dt = datetime.fromisoformat(value)
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            return None
    return dt.replace(tzinfo=dt.tzinfo or timezone.utc).astimezone(timezone.utc)


def parse(body, kind):
    if kind in IOC_FORMATS:
        items, latest, _ = ioc_summary(body, kind, parse_date)
        return len(items), latest
    text = body.decode('utf-8-sig')
    if kind == 'rss':
        root = ET.fromstring(text)
        if root.tag not in ('rss', '{http://www.w3.org/2005/Atom}feed', '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'):
            raise ValueError('Expected RSS/Atom, not an HTML/login page')
        items = root.findall('.//item') + root.findall('{http://www.w3.org/2005/Atom}entry')
        dates = [parse_date(e.text) for item in items for e in item.iter()
                 if e.tag.split('}')[-1] in ('pubDate', 'published', 'updated', 'date')]
        latest = max((d for d in dates if d), default=None)
        return len(items), latest
    if kind == 'kev':
        obj = json.loads(text)
        items = obj['vulnerabilities']
        if not isinstance(items, list) or any('cveID' not in i for i in items):
            raise ValueError('Unexpected KEV records')
        return len(items), parse_date(obj.get('dateReleased'))
    if kind == 'nvd':
        obj = json.loads(text)
        items = obj['vulnerabilities']
        if not isinstance(items, list):
            raise ValueError('Unexpected NVD schema')
        # Response timestamp is retrieval metadata, not newest vulnerability date.
        return len(items), None
    if kind == 'cve-record':
        obj = json.loads(text)
        if not obj.get('cveMetadata', {}).get('cveId', '').startswith('CVE-'):
            raise ValueError('Unexpected CVE record schema')
        return 1, None
    if kind == 'url-list':
        lines = [x.strip() for x in text.splitlines() if x.strip() and not x.startswith('#')]
        if any(not x.startswith(('https://', 'http://')) or '<' in x for x in lines):
            raise ValueError('Expected one URL per line')
        return len(lines), None
    raise ValueError('Unknown parser')


def assess(source, previous, body, timestamp):
    count, latest = parse(body, source['format'])
    ioc_details = ioc_summary(body, source['format'], parse_date)[2] if source['format'] in IOC_FORMATS else {}
    digest = hashlib.sha256(body).hexdigest()
    alerts = []
    if ioc_details.get('rejected_record_count', 0) / max(ioc_details.get('total_record_count', 0), 1) > .05:
        alerts.append('high-invalid-record-rate')
    if count == 0:
        alerts.append('empty-data')
    old_count = previous.get('count')
    if old_count and count and (count / old_count < .5 or count / old_count > 2):
        alerts.append('large-count-change')
    old_latest = parse_date(previous.get('latest_item_at'))
    if latest and old_latest and latest < old_latest:
        alerts.append('timestamp-regressed')
    if latest and latest > timestamp:
        alerts.append('future-timestamp')
    stale = latest and (timestamp - latest).total_seconds() > source['stale_after_hours'] * 3600
    if stale:
        alerts.append('review-freshness')
    changed = digest != previous.get('sha256')
    changed_at = timestamp.isoformat() if changed else previous.get('last_content_change_at', timestamp.isoformat())
    if not latest and not changed and (timestamp - parse_date(changed_at)).total_seconds() > source['stale_after_hours'] * 3600:
        alerts.append('review-unchanged-content')
    samples = ioc_details.get('samples', [])
    if source['format'] == 'rss':
        root = ET.fromstring(body.decode('utf-8-sig'))
        for item in (root.findall('.//item') + root.findall('{http://www.w3.org/2005/Atom}entry'))[:3]:
            title, link = '', ''
            for child in item:
                tag = child.tag.split('}')[-1]
                if tag == 'title':
                    title = ''.join(child.itertext()).strip()
                if tag == 'link' and child.attrib.get('rel', 'alternate') == 'alternate':
                    link = child.attrib.get('href') or (child.text or '').strip()
            if title and link.startswith(('https://', 'http://')):
                samples.append({'title': title, 'url': link})
        if count and not samples:
            alerts.append('missing-readable-items')
    elif source['format'] == 'kev':
        samples = [{'cve': i['cveID'], 'title': i.get('vulnerabilityName'), 'date': i.get('dateAdded')}
                   for i in json.loads(body)['vulnerabilities'][-3:]]
    elif source['format'] == 'nvd':
        for item in json.loads(body)['vulnerabilities'][:3]:
            record = item.get('cve', {})
            if record.get('id'):
                samples.append({'cve':record['id'], 'published':record.get('published')})
        if count and not samples:
            alerts.append('missing-readable-items')
    result = dict(count=count, samples=samples, latest_item_at=latest.isoformat() if latest else None,
                sha256=digest, changed=changed, last_content_change_at=changed_at,
                freshness='review' if stale else ('within-window' if latest else 'unknown'),
                alerts=alerts, content='valid', last_success_at=timestamp.isoformat())
    result.update(ioc_details)
    return result


def check(source, previous, opener, timestamp, route='direct'):
    result = dict(previous)
    result.update(id=source['id'], checked_at=timestamp.isoformat(), check_origin='local', alerts=[])
    if not source.get('endpoint'):
        result.pop('checked_at', None)
        result['evaluated_at'] = timestamp.isoformat()
        result.update(access='manual-reference' if source.get('access_mode') == 'manual' else 'needs-auth-or-access-review', content='not-checked', freshness='unknown')
        return result
    last = parse_date(previous.get('checked_at'))
    if last and (timestamp - last).total_seconds() < source['interval_hours'] * 3600:
        return previous
    result.pop('http_status', None)
    result.pop('final_url', None)
    result['check_origin'] = 'github-actions' if os.environ.get('GITHUB_ACTIONS') == 'true' else os.environ.get('INTEL_SHELF_ORIGIN', 'local')
    timeout = source.get('timeout_seconds', 25)
    endpoints = [source['endpoint']]
    mirror = source.get('mirror_endpoint')
    if mirror and mirror != source['endpoint']:
        endpoints.append(mirror)
    try:
        result['request_attempts'] = []
        body = None
        primary_error = None
        last_error = None
        for endpoint in endpoints:
            ep_route = route if endpoint == source['endpoint'] else route + '-mirror'
            req = urllib.request.Request(endpoint, headers={'User-Agent': 'intel-shelf/0.1 (manual public-source health checks)'})
            for attempt in range(2):
                started = monotonic()
                evidence = dict(started_at=now().isoformat(), requested_url=endpoint, route=ep_route)
                result['request_attempts'].append(evidence)
                try:
                    with opener.open(req, timeout=timeout) as response:
                        result.update(http_status=response.status, final_url=response.url)
                        evidence.update(http_status=response.status, final_url=response.url,
                                        content_type=getattr(response, 'headers', {}).get('Content-Type'))
                        body = response.read(12 * 1024 * 1024 + 1)
                    evidence.update(outcome='received', bytes_read=len(body))
                    break
                except (urllib.error.URLError, OSError) as network_error:
                    evidence.update(outcome='failed', error=str(network_error)[:400])
                    if isinstance(network_error, urllib.error.HTTPError):
                        failed_url = network_error.__dict__.get('url', endpoint)
                        evidence.update(http_status=network_error.code, final_url=failed_url,
                                        content_type=network_error.headers.get('Content-Type') if network_error.headers else None)
                        result.update(http_status=network_error.code, final_url=failed_url)
                    last_error = network_error
                    if endpoint == source['endpoint'] and primary_error is None:
                        primary_error = network_error
                    # Do not repeatedly hit authentication, throttling or policy responses.
                    if attempt or isinstance(network_error, urllib.error.HTTPError):
                        break
                finally:
                    evidence.update(at=now().isoformat(), elapsed_ms=round((monotonic() - started) * 1000))
            if body is not None:
                break
        if body is None:
            raise (primary_error or last_error) if (primary_error or last_error) else OSError('no response from any endpoint')
        result.update(access='reachable', consecutive_failures=0)
        if len(body) > 12 * 1024 * 1024:
            raise ValueError('Response exceeds 12 MiB limit')
        result.update(assess(source, previous, body, timestamp))
        result.pop('error', None)
    except Exception as exc:
        result.update(content='not-validated', freshness='unknown',
                      consecutive_failures=previous.get('consecutive_failures', 0) + 1)
        if not isinstance(exc, (ValueError, ET.ParseError, KeyError, UnicodeError)):
            result['access'] = 'fetch-failed'
        result['error'] = str(exc)[:400]
        result['alerts'] = ['fetch-or-parse-error']
        if result['consecutive_failures'] >= 3:
            result['alerts'].append('repeated-failure')
    result['alert_streaks'] = {alert: previous.get('alert_streaks', {}).get(alert, 0) + 1
                               for alert in result.get('alerts', [])}
    return result


def render(catalog, state):
    labels = {'reachable':'获取成功','fetch-failed':'获取失败','needs-auth-or-access-review':'待认证/条件核验',
              'manual-reference':'人工查阅入口',
              'valid':'基础解析通过','not-validated':'未通过验证','not-checked':'未检查',
              'within-window':'复核窗口内','review':'待复核','unknown':'未知'}
    timestamp = now()
    def usable(source):
        row = state.get(source['id'], {})
        checked = parse_date(row.get('checked_at'))
        return bool(source.get('use_status') != 'historical-only' and source.get('endpoint') and checked and
                    (timestamp-checked).total_seconds() <= max(24, source['interval_hours']*2)*3600 and
                    row.get('access') == 'reachable' and row.get('content') == 'valid' and
                    row.get('count', 0) > 0 and not row.get('alerts'))
    active = [s for s in catalog if usable(s)]
    lines = ['# 来源目录', '', '## 当前可读取的公开入口', '',
             f'已验证可读取 {len(active)} 个；受限、异常及检查过期的来源单列在下方，不计入可用数量。', '',
             '这是入口可用性验证，不是情报准确率认证或公司使用许可。RSS 用于发现文章，不是历史 CVE 搜索 API。时间为 UTC。', '']
    for category in dict.fromkeys(c for s in catalog for c in s['categories']):
        if not any(category in s['categories'] for s in active):
            lines += ['## ' + category, '']
            manual = [s for s in catalog if category in s['categories'] and s.get('access_mode') == 'manual']
            if manual:
                for source in manual:
                    lines += [f"- [{source['name']}]({source['url']})：人工查阅入口。{source['purpose']}；{source['limits']}", '']
            else:
                lines += ['暂无通过本次可用性条件的公开数据入口；待接入/异常项见下方。', '']
            continue
        lines += ['## ' + category, '', '| 来源 | 用途 / 限制 | 获取 | 内容 | 新鲜度 | 检查时间 |', '|---|---|---|---|---|---|']
        for source in catalog:
            if category not in source['categories']:
                continue
            if not usable(source):
                continue
            row = state.get(source['id'], {})
            endpoint = row.get('final_url') or source['endpoint']
            cells = [f"[{source['name']}]({source['url']}) · [数据入口]({endpoint})", source['purpose'] + '；' + source['limits'],
                     labels.get(row.get('access'), '未检查'), labels.get(row.get('content'), '未检查'), labels.get(row.get('freshness'), '未知'), row.get('checked_at', '—')]
            lines.append('| ' + ' | '.join(str(x).replace('|', '\\|').replace('\n', ' ') for x in cells) + ' |')
        lines.append('')
    lines += ['## 待接入或异常的来源（不计入可用）', '', '历史参考来源也单列于此；人工网页入口列于对应类别。', '', '| 来源 | 原因 | 最后成功获取 |', '|---|---|---|']
    for source in catalog:
        if usable(source) or source.get('access_mode') == 'manual':
            continue
        row = state.get(source['id'], {})
        reason = labels.get(row.get('access'), '未检查')
        if row.get('access') == 'reachable':
            reason = '检查已过期或内容异常，需复核'
            if row.get('alerts'):
                reason += '：' + ', '.join(row['alerts'])
        if source.get('use_status') == 'historical-only':
            reason = '仅历史参考；官方当前数据集状态见来源档案，未作为活跃情报接入'
        if row.get('error'):
            reason += '：' + row['error']
        lines.append('| [' + source['name'] + '](' + source['url'] + ') | ' + reason.replace('|','\\|').replace('\n',' ') + ' | ' + row.get('last_success_at','—') + ' |')
    lines += ['', '## 本次获取的内容示例', '', '只展示来自 feed 的标题/引用，不访问这些链接；不代表已阅读或认可文章结论。', '']
    for source in active:
        for sample in state[source['id']].get('samples', [])[:1]:
            if sample.get('value'):
                lines.append('- ' + source['name'] + '：`' + sample['value'].replace('`', '').replace('\n', ' ') + '`')
                continue
            label = sample.get('title') or sample.get('cve') or sample.get('value') or ''
            label = label.replace('[', '').replace(']', '').replace('\n', ' ')
            lines.append('- ' + source['name'] + '：' + (f"[{label}]({sample['url']})" if sample.get('url') else label))
    lines += ['', '## 恶意指标数据核验', '', '| 来源 | 有效记录/去重指标/剔除条数 | 类型分布 | 时间含义与最新日期 | 原始引用条数 |', '|---|---|---|---|---|']
    for source in catalog:
        if source['format'] not in IOC_FORMATS:
            continue
        row = state.get(source['id'], {})
        lines.append('| ' + source['name'] + ' | ' + str(row.get('record_count','—')) + '/' + str(row.get('unique_indicator_count','—')) + '/' + str(row.get('rejected_record_count','—')) + ' | ' + str(row.get('indicator_types', {})) + ' | ' + str(row.get('time_basis','未知')) + ' / ' + str(row.get('latest_item_at') or '未知') + ' | ' + str(row.get('reference_count','—')) + ' |')
    lines += ['', '指标示例均去武器化；不生成封禁清单。上游 online 状态不代表本次已验证在线，报告时间也不等于指标仍有效。']
    return '\n'.join(lines)


def review_tasks(catalog, state, feedback, timestamp):
    tasks = []
    for source in catalog:
        sid = source['id']
        row = state.get(sid, {})
        reviews = [r for r in feedback if r.get('source_id') == sid and r.get('reviewed_on')]
        latest = max((r['reviewed_on'] for r in reviews), default=None)
        baseline = parse_date(latest or source.get('documentation_reviewed_on'))
        reasons = set(row.get('alerts', []))
        if row.get('consecutive_failures', 0) < 3:
            reasons.discard('fetch-or-parse-error')
        if source.get('use_status') == 'historical-only':
            reasons.discard('review-freshness')
        if baseline is None or (timestamp.date() - baseline.date()).days >= 30:
            reasons.add('periodic-review')
        if reasons:
            count = max(row.get('consecutive_failures', 0),
                        max((row.get('alert_streaks', {}).get(r, 0) for r in reasons), default=0))
            tasks.append(dict(source_id=sid, reasons=sorted(reasons), checked_at=row.get('checked_at'),
                              last_reviewed_on=latest, error=row.get('error'),
                              consecutive_problem_checks=count,
                              action='repair-required' if count >= 3 else 'review'))
    return {'schema_version': 1, 'review_interval_days': 30, 'tasks': tasks}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proxy', help='Process-only HTTP/SOCKS is not implied; HTTP proxy URL')
    parser.add_argument('--render-only', action='store_true')
    parser.add_argument('--retry-failed', action='store_true', help='Retry currently failed sources before their normal interval')
    parser.add_argument('--force', action='store_true', help='Recheck public endpoints, ignoring the normal interval')
    parser.add_argument('--source', help='Check only this catalog source ID, retaining other observations')
    args = parser.parse_args()
    catalog = json.loads((ROOT / 'sources/catalog.json').read_text(encoding='utf-8'))
    ids = [s['id'] for s in catalog]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate source IDs')
    if args.source and args.source not in ids:
        parser.error('Unknown source ID')
    state_path = ROOT / 'data/status.json'
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    if not args.render_only:
        # Ignore inherited persistent proxy configuration unless explicitly selected.
        proxy = {'https': args.proxy, 'http': args.proxy} if args.proxy else {}
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxy))
        timestamp = now()
        for source in catalog:
            if args.source and source['id'] != args.source:
                continue
            previous = dict(state.get(source['id'], {}))
            if args.force or (args.retry_failed and previous.get('consecutive_failures', 0)):
                previous.pop('checked_at', None)
            state[source['id']] = check(source, previous, opener, timestamp, 'proxy' if args.proxy else 'direct')
            print(source['id'], state[source['id']].get('access'), flush=True)
        atomic(state_path, json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        atomic(ROOT / ('data/history/' + timestamp.strftime('%Y%m%dT%H%M%S%fZ') + '.json'), json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    atomic(ROOT / 'DIRECTORY.md', render(catalog, state))
    issues = [{'id': k, 'alerts': v.get('alerts'), 'error': v.get('error'), 'checked_at': v.get('checked_at')}
              for k, v in state.items() if v.get('alerts')]
    atomic(ROOT / 'data/review-queue.json', json.dumps(issues, ensure_ascii=False, indent=2) + '\n')
    feedback = json.loads((ROOT / 'data/feedback.json').read_text(encoding='utf-8'))
    tasks = review_tasks(catalog, state, feedback, now())
    atomic(ROOT / 'index.html', page(catalog, state, feedback, tasks, now()))
    atomic(ROOT / 'data/maintenance-tasks.json', json.dumps(tasks, ensure_ascii=False, indent=2) + '\n')
    print('AI maintenance tasks:', len(tasks['tasks']))
    print('Review items:', len(issues))


if __name__ == '__main__':
    main()


