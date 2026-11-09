"""Source-specific contracts. Inspect feed data only; never follow item URLs."""
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(source, body, parse_date):
    """Additional semantic checks beyond the shared format parser."""
    profile = source.get('check_profile')
    if not profile:  # Generic fixtures / sources not yet assigned a contract.
        return
    if profile in ('unit42', 'talos', 'checkpoint', 'dfir-report'):
        require(source['format'] == 'rss', 'RSS contract/parser mismatch')
        root = ET.fromstring(body.decode('utf-8-sig'))
        items = root.findall('.//item') + root.findall('{http://www.w3.org/2005/Atom}entry')
        for item in items:
            title, links, dates = '', [], []
            for child in item:
                name = child.tag.split('}')[-1]
                if name == 'title':
                    title = ''.join(child.itertext()).strip()
                elif name == 'link' and child.attrib.get('rel', 'alternate') == 'alternate':
                    links.append(child.attrib.get('href') or (child.text or '').strip())
                elif name in ('pubDate', 'published', 'updated', 'date'):
                    dates.append(child.text)
            require(bool(title), profile + ': article title missing')
            require(any(urlsplit(url).scheme in ('http', 'https') and urlsplit(url).hostname for url in links),
                    profile + ': article reference missing')
            require(bool(dates) and all(parse_date(d) for d in dates), profile + ': article date missing/invalid')
    elif profile == 'cisa-kev':
        require(source['format'] == 'kev', 'KEV contract/parser mismatch')
        obj = json.loads(body.decode('utf-8-sig'))
        items = obj['vulnerabilities']
        require(isinstance(obj.get('catalogVersion'), str), 'KEV catalogVersion missing')
        require(parse_date(obj.get('dateReleased')) is not None, 'KEV release date missing/invalid')
        require(type(obj.get('count')) is int and obj['count'] == len(items), 'KEV count does not match records')
        for row in items:
            require(bool(re.fullmatch(r'CVE-\d{4}-\d{4,}', row.get('cveID', ''))), 'KEV CVE ID invalid')
            require(parse_date(row.get('dateAdded')) is not None, 'KEV dateAdded missing/invalid')
    elif profile == 'nvd':
        require(source['format'] == 'nvd', 'NVD contract/parser mismatch')
        obj = json.loads(body.decode('utf-8-sig'))
        require(type(obj.get('totalResults')) is int, 'NVD totalResults missing')
        for row in obj['vulnerabilities']:
            cve = row.get('cve', {})
            require(bool(re.fullmatch(r'CVE-\d{4}-\d{4,}', cve.get('id', ''))), 'NVD CVE ID missing/invalid')
            require(parse_date(cve.get('published')) is not None, 'NVD publication date missing/invalid')
            require(parse_date(cve.get('lastModified')) is not None, 'NVD modification date missing/invalid')
    elif profile == 'circl':
        require(source['format'] == 'cve-record', 'CIRCL contract/parser mismatch')
        obj = json.loads(body.decode('utf-8-sig'))
        require(obj.get('cveMetadata', {}).get('cveId') == source.get('probe_cve'), 'CIRCL returned a different probe CVE')
        require(isinstance(obj.get('containers', {}).get('cna'), dict), 'CIRCL CNA container missing')
    elif profile in ('tweetfeed', 'feodo', 'c2intel', 'openphish'):
        formats = {'tweetfeed': 'tweetfeed-csv', 'feodo': 'feodo-json', 'c2intel': 'c2-csv', 'openphish': 'url-list'}
        require(source['format'] == formats[profile], profile + ': contract/parser mismatch')
        # Their format parsers validate every row, provenance and time semantics.
    else:
        raise ValueError('Unknown source check_profile: ' + str(profile))


def display_status(source, row, timestamp):
    """One availability rule shared by Markdown and HTML."""
    from datetime import datetime
    if source.get('use_status') == 'historical-only':
        return '仅历史参考'
    if source.get('access_mode') == 'manual':
        return '人工查阅'
    if not source.get('endpoint'):
        return '待接入'
    checked = row.get('checked_at')
    recent = checked and (timestamp - datetime.fromisoformat(checked.replace('Z', '+00:00'))).total_seconds() <= max(24, source['interval_hours'] * 2) * 3600
    if not recent:
        return '待更新检查'
    if row.get('alerts') or row.get('content') != 'valid' or row.get('access') != 'reachable' or not row.get('count'):
        return '检查异常'
    return '入口可读取'
