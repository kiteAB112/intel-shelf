"""Parse public indicator feeds as data; never resolve or visit indicator values."""
import csv
import io
import ipaddress
import json
import re
from collections import Counter
from urllib.parse import urlsplit


def validate_indicator(kind, value):
    if kind in ('ip', 'ipv4', 'ipv6'):
        ipaddress.ip_address(value)
    elif kind in ('md5', 'sha256'):
        if not re.fullmatch('[0-9a-fA-F]{%d}' % (32 if kind == 'md5' else 64), value):
            raise ValueError('Invalid hash')
    elif kind == 'url':
        url = urlsplit(value)
        if url.scheme not in ('http', 'https') or not url.hostname:
            raise ValueError('Invalid URL')
    elif kind == 'domain':
        try:
            ascii_domain = value.encode('idna').decode('ascii')
        except UnicodeError:
            raise ValueError('Invalid IDN domain')
        if len(ascii_domain) > 253 or '.' not in ascii_domain or any(
                not re.fullmatch(r'[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?', label)
                for label in ascii_domain.rstrip('.').split('.')):
            raise ValueError('Invalid domain')
    else:
        raise ValueError('Unsupported IOC type: ' + kind)


def defang(value):
    return value.replace('https://', 'hxxps://').replace('http://', 'hxxp://').replace('.', '[.]')


def records(body, kind):
    text = body.decode('utf-8-sig')
    result = []
    if kind == 'tweetfeed-csv':
        for row in csv.reader(io.StringIO(text)):
            if not row:
                continue
            # Published CSV has no header: never skip its first record.
            if len(row) != 6:
                raise ValueError('TweetFeed expected six columns')
            date, reporter, ioc_type, value, tags, reference = row
            validation_error = None
            try:
                validate_indicator(ioc_type, value)
            except ValueError as exc:
                validation_error = str(exc)
            ref = urlsplit(reference)
            if ref.scheme != 'https' or ref.hostname not in ('twitter.com', 'x.com', 'www.twitter.com', 'www.x.com'):
                raise ValueError('Unexpected TweetFeed reference host')
            result.append(dict(type=ioc_type, value=value, reported_at=date,
                               reporter=reporter, tags=tags.split(), reference=reference,
                               observed_at=None, current_validity='unknown', validation_error=validation_error))
    elif kind == 'feodo-json':
        obj = json.loads(text)
        if not isinstance(obj, list):
            raise ValueError('Feodo expected array')
        for row in obj:
            validate_indicator('ip', row['ip_address'])
            if not isinstance(row['port'], int) or not 0 < row['port'] <= 65535:
                raise ValueError('Invalid port')
            if row['status'] not in ('online','offline'):
                raise ValueError('Unknown Feodo status')
            result.append(dict(type='ip', value=row['ip_address'], port=row['port'],
                               observed_at=row['last_online'], first_seen=row['first_seen'],
                               upstream_status=row['status'], malware=row['malware'],
                               current_validity='unknown'))
    elif kind == 'c2-csv':
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames != ['#ip','ioc']:
            raise ValueError('C2Intel expected #ip,ioc header')
        for row in reader:
            validate_indicator('ip', row['#ip'])
            if not row['ioc']:
                raise ValueError('Missing C2 label')
            result.append(dict(type='ip', value=row['#ip'], label=row['ioc'],
                               observed_at=None, current_validity='unknown'))
    elif kind == 'ip-list':
        for value in text.splitlines():
            value = value.strip()
            if value and not value.startswith('#'):
                validate_indicator('ip', value)
                result.append(dict(type='ip', value=value, observed_at=None, current_validity='unknown'))
    else:
        raise ValueError('Unknown IOC parser')
    return result


def summary(body, kind, parse_date):
    all_items = records(body, kind)
    invalid = [i for i in all_items if i.get('validation_error')]
    items = [i for i in all_items if not i.get('validation_error')]
    dates = []
    for item in items:
        for field in ('reported_at', 'observed_at'):
            if item.get(field):
                date = parse_date(item[field])
                if date is None:
                    raise ValueError('Invalid record timestamp')
                dates.append(date)
    # A small provenance-bearing sample, never an executable/clickable IOC URL.
    samples = []
    for item in sorted(items, key=lambda i:i.get('reported_at') or i.get('observed_at') or '', reverse=True)[:3]:
        sample = dict(item)
        sample['value'] = defang(sample['value'])
        samples.append(sample)
    counts = dict(Counter(item['type'] for item in items))
    return items, max(dates, default=None), dict(samples=samples, indicator_types=counts,
          time_basis='report-time' if kind == 'tweetfeed-csv' else ('last-online' if kind == 'feodo-json' else 'not-provided'),
          upstream_status_counts=dict(Counter(i['upstream_status'] for i in items if 'upstream_status' in i)),
          reference_count=sum(bool(i.get('reference')) for i in items),
          total_record_count=len(all_items), rejected_record_count=len(invalid),
          rejected_samples=[{'type':i['type'],'value':defang(i['value']),'reason':i['validation_error']} for i in invalid[:3]],
          record_count=len(items), unique_indicator_count=len(set((i['type'],i['value']) for i in items)))
