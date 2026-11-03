"""Render the local, offline source directory."""
from datetime import datetime
from html import escape
from urllib.parse import urlsplit


def link(url, label):
    if url and urlsplit(url).scheme in ('http', 'https'):
        return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'
    return ''


def page(catalog, state, feedback, tasks, timestamp):
    categories = list(dict.fromkeys(category for source in catalog for category in source['categories']))
    rank = {category: index for index, category in enumerate(categories)}
    pending = {task['source_id']: task['reasons'] for task in tasks['tasks']}
    cards = []
    rows = []
    for source in sorted(catalog, key=lambda s: (rank[s['categories'][0]], s['name'].casefold())):
        sid = source['id']
        row = state.get(sid, {})
        checked = row.get('checked_at')

        recent = checked and (timestamp - datetime.fromisoformat(checked.replace('Z', '+00:00'))).total_seconds() <= max(24, source['interval_hours'] * 2) * 3600
        if source.get('use_status') == 'historical-only':
            status = '仅历史参考'
        elif source.get('access_mode') == 'manual':
            status = '人工查阅'
        elif not source.get('endpoint'):
            status = '待接入'
        elif not recent:
            status = '待更新检查'
        elif row.get('alerts') or row.get('content') != 'valid' or row.get('access') != 'reachable' or not row.get('count'):
            status = '检查异常'
        else:
            status = '入口可读取'
        fields = [('类别', ' · '.join(source['categories'])), ('查询类型', ' / '.join(source['capabilities'])),
                  ('时间含义', source['time_semantics']), ('使用范围', source['usage_scope']),
                  ('最近检查', checked or '无请求记录'), ('原始告警', ', '.join(row.get('alerts', [])) or '无'),
                  ('复核待办', ', '.join(pending.get(sid, [])) or '无')]
        details = ''.join(f'<dt>{escape(k)}</dt><dd>{escape(v)}</dd>' for k, v in fields)
        for review in feedback:
            if review['source_id'] == sid:
                evidence = ' '.join(link(url, f'依据 {i}') for i, url in enumerate(review.get('evidence', []), 1))
                details += f'<dt>维护决定</dt><dd>{escape(review["decision"])} {evidence}</dd>'
        cats = escape('|'.join(source['categories']), quote=True)
        rows.append(f"""<tr><td><strong>{escape(source['name'])}</strong><br>{link(source['url'], '官网')} {link(source.get('endpoint'), '数据入口')}</td>
<td>{escape(' · '.join(source['categories']))}</td><td>{escape(source['purpose'])}
<details><summary>限制与档案</summary><p>{escape(source['limits'])}</p><dl>{details}</dl></details></td>
<td>{status}</td><td>{escape(checked[:16].replace('T', ' ') if checked else '无请求记录')}</td></tr>""")
        cards.append(f"""<article data-categories="{cats}"><small>{escape(source['categories'][0])}</small>
<h2>{escape(source['name'])}</h2><b>{status}</b><p>{escape(source['purpose'])}</p>
<p class="limit">{escape(source['limits'])}</p><details><summary>查看档案与复核依据</summary><dl>{details}</dl></details>
<footer>{link(source['url'], '官网')} {link(source.get('endpoint'), '数据入口')}</footer></article>""")
    options = ''.join(f'<option>{escape(c)}</option>' for c in categories)
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Intel Shelf · 情报来源目录</title><style>
*{{box-sizing:border-box}}body{{background:#f2f4ef;color:#17382e;font:16px/1.6 system-ui,sans-serif;margin:auto;max-width:1250px;padding:clamp(18px,4vw,55px)}}header{{border-bottom:2px solid #245b49;padding-bottom:18px}}h1{{font-size:clamp(32px,5vw,56px);margin:.15em 0}}small,b{{color:#316654}}nav{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:22px 0}}input,select{{font:inherit;padding:6px;max-width:100%}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr));gap:16px;align-items:start}}article{{background:white;padding:20px;border:1px solid #cbd8d0;border-radius:10px;overflow-wrap:anywhere}}h2{{margin:.25em 0}}b{{background:#edf2ed;padding:2px 7px}}.limit,dt{{color:#52665c}}summary{{cursor:pointer}}dd{{margin:0 0 8px}}footer{{border-top:1px solid #dde5de;margin-top:12px;padding-top:10px}}a{{color:#176654;margin-right:8px}}
[hidden]{{display:none!important}}#sheet{{overflow-x:auto;background:white;border:1px solid #cbd8d0;border-radius:10px}}table{{border-collapse:collapse;width:100%;min-width:700px;font-size:15px}}th,td{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #dde5de}}th{{background:#e3ebe4}}tbody tr:hover{{background:#f6f8f4}}td:nth-child(3){{width:36%}}td:last-child{{font-variant-numeric:tabular-nums}}td summary{{color:#316654;font-size:.9em}}
</style><header><small>INTEL SHELF / 来源目录</small><h1>情报来源目录</h1>
{len(catalog)} 个来源 · {len(categories)} 个类别 · {len(pending)} 个复核待办<br>
快照生成于 {timestamp.strftime('%Y-%m-%d %H:%M UTC')}。入口检查反映当时的可读取性，具体情报的有效期需单独核实。</header>
<nav><label>搜索 <input id="q" type="search" placeholder="名称、用途或指标类型"></label>
<label>类别 <select id="cat"><option value="">全部类别</option>{options}</select></label>
<label>视图 <select id="view"><option value="table">表格</option><option value="cards">卡片</option></select></label><output id="count" aria-live="polite"></output></nav>
<section id="sheet"><table aria-label="情报来源目录"><thead><tr><th>来源与入口</th><th>类别</th><th>用途</th><th>快照状态</th><th>最近检查（UTC）</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
<main hidden>{''.join(cards)}</main><script>
const q=document.querySelector('#q'),cat=document.querySelector('#cat'),cards=[...document.querySelectorAll('article')];
function filter(){{let n=0;for(const card of cards){{card.hidden=!(card.textContent.toLowerCase().includes(q.value.trim().toLowerCase())&&(!cat.value||card.dataset.categories.split('|').includes(cat.value)));if(!card.hidden)n++;}}document.querySelector('#count').textContent=n?'显示 '+n+' 个来源':'没有匹配的来源';}}
const rows=[...document.querySelectorAll('tbody tr')],view=document.querySelector('#view');
function refresh(){{filter();rows.forEach((row,i)=>row.hidden=cards[i].hidden);document.querySelector('main').hidden=view.value!=='cards';document.querySelector('#sheet').hidden=view.value!=='table';}}
q.oninput=cat.onchange=view.onchange=refresh;refresh();
</script></html>"""

