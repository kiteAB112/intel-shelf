"""Small public-intelligence query router. Inputs are never network targets."""
import argparse
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import quote, urlsplit
from ioc_formats import records, defang, validate_indicator

ROOT = Path(__file__).resolve().parents[1]


def identify(value):
    value = value.strip().replace('[.]', '.').replace('hxxps://', 'https://').replace('hxxp://', 'http://')
    if re.fullmatch(r'CVE-\d{4}-\d{4,}', value, re.I):
        return 'cve', value.upper()
    try:
        return 'ip', str(ipaddress.ip_address(value))
    except ValueError:
        pass
    for kind, length in [('md5', 32), ('sha256', 64)]:
        if re.fullmatch('[0-9a-fA-F]{%d}' % length, value):
            return kind, value.lower()
    if value.startswith(('http://', 'https://')):
        validate_indicator('url', value)
        parsed = urlsplit(value)
        if parsed.username or parsed.password:
            raise ValueError('Do not submit URLs containing credentials')
        return 'url', value
    validate_indicator('domain', value)
    return 'domain', value.rstrip('.').encode('idna').decode('ascii').lower()


def select_sources(catalog, kind, context):
    routes = []
    for source in catalog:
        if kind not in source.get('capabilities', []):
            continue
        mode = source.get('query_mode', 'manual')
        reason = None
        if source.get('use_status') == 'historical-only':
            reason = 'historical-only'
        elif context == 'company' and source.get('usage_scope') == 'noncommercial-research-only':
            reason = 'noncommercial-research-only'
        elif not source.get('endpoint') and mode != 'manual':
            reason = 'not-configured'
        routes.append(dict(source_id=source['id'], mode=mode, skip_reason=reason,
                           url=source['url'], purpose=source['purpose'], limits=source['limits'],
                           terms_url=source.get('terms_url'), query_note=source.get('query_note')))
    return routes


def english(descriptions):
    return next((x.get('value', '') for x in descriptions if x.get('lang') == 'en'), '')


def cve_facts(source_id, obj, value):
    if source_id == 'nvd':
        if not isinstance(obj, dict) or not isinstance(obj.get('vulnerabilities'), list):
            raise ValueError('Unexpected NVD schema')
        rows = [i['cve'] for i in obj['vulnerabilities'] if i.get('cve', {}).get('id') == value]
        if obj['vulnerabilities'] and not rows:
            raise ValueError('NVD returned a different CVE')
        return [dict(cve=r['id'], published=r.get('published'), modified=r.get('lastModified'),
                     description=english(r.get('descriptions', [])), metrics=r.get('metrics', {}),
                     references=[x['url'] for x in r.get('references', []) if x.get('url')]) for r in rows]
    if source_id == 'cisa-kev':
        if not isinstance(obj, dict) or not isinstance(obj.get('vulnerabilities'), list):
            raise ValueError('Unexpected KEV schema')
        return [dict(cve=r['cveID'], catalog_date=obj.get('dateReleased'),
                     added=r.get('dateAdded'), description=r.get('shortDescription'),
                     required_action=r.get('requiredAction'), ransomware=r.get('knownRansomwareCampaignUse'),
                     vendor=r.get('vendorProject'), product=r.get('product'), notes=r.get('notes'))
                for r in obj['vulnerabilities'] if r.get('cveID') == value]
    if source_id == 'circl':
        if obj == {} or obj is None:
            return []
        if obj.get('cveMetadata', {}).get('cveId') != value:
            raise ValueError('CIRCL returned a missing/different CVE')
        cna = obj.get('containers', {}).get('cna', {})
        return [dict(cve=value, record_state=obj['cveMetadata'].get('state'),
                     published=obj['cveMetadata'].get('datePublished'), modified=obj['cveMetadata'].get('dateUpdated'),
                     description=english(cna.get('descriptions', [])),
                     affected=cna.get('affected', []), metrics=cna.get('metrics', []),
                     references=[r['url'] for r in cna.get('references', []) if r.get('url')])]
    raise ValueError('Unsupported CVE adapter')


def indicator_matches(source, body, kind, value):
    if source['format'] == 'url-list':
        lines = [v.strip() for v in body.decode('utf-8-sig').splitlines() if v.strip() and not v.startswith('#')]
        for line in lines:
            validate_indicator('url', line)
        items = [dict(type='url', value=v, reported_at=None, observed_at=None, reference=source['url']) for v in lines]
    else:
        items = records(body, source['format'])
    matches = []
    for item in items:
        if item.get('validation_error') or item['type'] != kind:
            continue
        try:
            _, normalized = identify(item['value'])
        except ValueError:
            continue
        if normalized == value:
            match = dict(item)
            match['value'] = defang(item['value'])
            match['current_validity'] = 'unknown'
            matches.append(match)
    return matches, len(items)


def fetch(opener, url):
    # Only catalog-approved source URLs reach here; a user IOC never becomes url.
    request = urllib.request.Request(url, headers={'User-Agent':'intel-shelf/0.1 public research'})
    with opener.open(request, timeout=25) as response:
        body = response.read(12*1024*1024+1)
        if len(body) > 12*1024*1024:
            raise ValueError('Response exceeds 12 MiB')
        return body, response.status, response.url


def collect(catalog, kind, value, context, opener):
    routes = select_sources(catalog, kind, context)
    sources = {s['id']:s for s in catalog}
    results = []
    for route in routes:
        row = dict(route, requested_at=datetime.now(timezone.utc).isoformat())
        source = sources[route['source_id']]
        if route['skip_reason']:
            row['outcome'] = 'skipped'
        elif route['mode'] == 'manual':
            row['outcome'] = 'manual-follow-up'
            row['search_terms'] = value
        else:
            url = source.get('query_endpoint', source['endpoint']).replace('{value}', quote(value, safe=''))
            row['requested_url'] = url
            try:
                body, http_status, final_url = fetch(opener, url)
                row.update(http_status=http_status, final_url=final_url,
                           retrieved_at=datetime.now(timezone.utc).isoformat(), response_sha256=hashlib.sha256(body).hexdigest())
                if kind == 'cve':
                    matches = cve_facts(source['id'], json.loads(body), value)
                else:
                    matches, count = indicator_matches(source, body, kind, value)
                    row['searched_records'] = count
                row.update(outcome='matched' if matches else 'no-match-in-response', match_count=len(matches), matches=matches[:100],
                           truncated=len(matches)>100)
            except Exception as exc:
                row.update(outcome='fetch-or-parse-failed', error=str(exc)[:400])
        results.append(row)
    return results


def render(request, results):
    statuses = {'matched':'找到记录','no-match-in-response':'本次返回中未匹配','fetch-or-parse-failed':'获取/解析失败',
                'manual-follow-up':'需人工/AI查阅','skipped':'未查询'}
    label = defang(request['value']) if request['kind'] != 'cve' else request['value']
    lines = ['# 查询资料包：`' + label.replace('`','') + '`', '',
             '这是自动收集结果，尚不是完成的研判。未命中不等于安全；失败不等于没有情报。', '',
             f"用途：{request['purpose']}；使用场景：{request['context']}；时间：{request['created_at']}。内部资产情况未知。", '',
             '| 来源 | 结果 | 说明 |', '|---|---|---|']
    for r in results:
        note = r.get('error') or r.get('skip_reason') or r['limits']
        lines.append('| ' + r['source_id'] + ' | ' + statuses[r['outcome']] + ' | ' + str(note).replace('|','\\|').replace('\n',' ') + ' |')
    for r in results:
        if not r.get('matches'):
            continue
        lines += ['', '## ' + r['source_id'], '', '数据来源：' + r['requested_url'], '',
                  '获取时间：' + r['retrieved_at'], '', '```json', json.dumps(r['matches'],ensure_ascii=False,indent=2), '```']
    lines += ['', '## 接下来的调查', '',
              '按 workflows/investigate.md 完成原始公告与事件报告核对，将结论写入 analysis.md。',
              'CVE：区分公开PoC/实际利用/活动关联；指标：核查报告时间、角色与引用，不能自动归因或封禁。',
              'RSS只覆盖当前返回窗口，不能作为历史CVE的完整检索结果。需要沿厂商公告/研究报告引用继续查询。']
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('value', help='Public CVE/IP/domain/URL/MD5/SHA256; never fetched as a target')
    parser.add_argument('--purpose', choices=['triage','hunt'], default='triage')
    parser.add_argument('--context', choices=['research','company'], default='research')
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--proxy')
    args = parser.parse_args()
    kind, value = identify(args.value)
    catalog = json.loads((ROOT/'sources/catalog.json').read_text(encoding='utf-8'))
    request = dict(value=value,kind=kind,purpose=args.purpose,context=args.context,created_at=datetime.now(timezone.utc).isoformat(),
                   scope='public-intelligence-only',asset_context='not-provided')
    if args.plan_only:
        print(json.dumps(dict(request=request,routes=select_sources(catalog,kind,args.context)),ensure_ascii=False,indent=2))
        return
    proxy = {'http':args.proxy,'https':args.proxy} if args.proxy else {}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxy))
    results = collect(catalog,kind,value,args.context,opener)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    # No user-controlled file path components.
    run=ROOT/'data/queries'/(stamp+'-'+hashlib.sha256(value.encode()).hexdigest()[:8])
    run.mkdir(parents=True)
    (run/'result.json').write_text(json.dumps(dict(request=request,results=results),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (run/'brief.md').write_text(render(request,results),encoding='utf-8')
    (run/'analysis.md').write_text((ROOT/'templates/analysis.md').read_text(encoding='utf-8'),encoding='utf-8')
    print('Query:',run)
    for row in results:
        print(row['source_id'], row['outcome'], row.get('match_count',''))
    automatic = [r for r in results if r['outcome'] not in ('manual-follow-up','skipped')]
    if not automatic or all(r['outcome']=='fetch-or-parse-failed' for r in automatic):
        raise SystemExit(1)


if __name__ == '__main__': main()
