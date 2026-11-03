"""Career Radar: public job feeds and configurable employer ATS boards.
No third-party packages, credentials or scraping required.
"""
import datetime as dt
import html
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOW = dt.datetime.now(dt.timezone.utc)
TARGET = ROOT / 'data' / 'jobs.json'
HEADERS = {'User-Agent': 'CareerRadar/2.0 (personal job listing reader)', 'Accept': 'application/json'}
TITLES = ('key account', 'account manager', 'account director', 'strategic account',
          'customer success', 'customer engagement', 'client relationship',
          'business development', 'commercial manager', 'commercial director',
          'commercial lead', 'head of commercial', 'sales director', 'head of sales',
          'vp sales', 'vice president sales', 'sales manager', 'partnership',
          'revenue director', 'enterprise account', 'regional director', 'country manager')
LOCAL = ('copenhagen', 'københavn', 'kobenhavn', 'hellerup', 'lyngby', 'gentofte',
         'ballerup', 'glostrup', 'frederiksberg', 'ørestad', 'oresund', 'sjælland',
         'zealand', 'denmark', 'danmark', 'malmö', 'malmo', 'lund', 'skåne',
         'skane', 'helsingborg', 'sweden', 'sverige')
REMOTE = ('remote', 'europe', 'emea', 'eu only', 'eu/uk', 'worldwide', 'anywhere')
SECTORS = ('maritime', 'shipping', 'marine', 'energy', 'sustainab', 'industrial',
           'saas', 'technology', 'decarbon', 'logistics', 'cleantech')


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=22) as response:
        return json.load(response)


def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', str(value or '')))).strip()


def date(value):
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value / (1000 if value > 1e11 else 1), dt.timezone.utc).date().isoformat()
    match = re.match(r'\d{4}-\d{2}-\d{2}', str(value or ''))
    return match.group() if match else NOW.date().isoformat()


def relevant(job):
    title = job['title'].lower()
    loc = job['location'].lower()
    if not any(word in title for word in TITLES):
        return False
    # A country-wide job feed should not be mistaken for an eligible local role.
    # Include local openings, EU/EMEA remote roles, and unspecified locations from
    # configured employer boards (these get a lower geography score).
    if any(word in loc for word in LOCAL):
        return True
    if any(word in loc for word in REMOTE):
        return not any(word in loc for word in ('united states only', 'us only', 'canada only', 'latam only'))
    return job['source'].startswith(('Greenhouse', 'Lever')) and not loc


def rating(job):
    title = job['title'].lower()
    body = (job.get('description', '') + ' ' + job['company']).lower()
    loc = job['location'].lower()
    result = 5.0
    if any(t in title for t in ('customer success', 'strategic account', 'key account', 'account director', 'commercial manager', 'commercial director', 'partnership')):
        result += 1.8
    elif any(t in title for t in ('business development', 'head of sales', 'sales director', 'vp sales')):
        result += 1.4
    else:
        result += 0.7
    if any(t in body for t in SECTORS):
        result += 0.8
    if any(t in loc for t in ('copenhagen', 'københavn', 'hellerup', 'malmö', 'malmo', 'lund')):
        result += 1.4
    elif any(t in loc for t in LOCAL):
        result += 1.0
    elif any(t in loc for t in REMOTE):
        result += 0.3
    if any(t in body for t in ('cold calling', 'door-to-door', 'commission only')):
        result -= 1.0
    return round(max(1, min(10, result)), 1)


def add(jobs, *, source, identity, title, company, location, description, url, posted):
    if not url or not title:
        return
    jobs.append({'id': f'{source}:{identity}', 'title': clean(title),
                 'company': clean(company), 'location': clean(location),
                 'description': clean(description)[:1200], 'url': str(url),
                 'date': date(posted), 'source': source})


def main():
    jobs, errors, sources = [], [], []
    try:
        # Arbeitnow pages are not guaranteed to be exhaustive; 1–4 improve coverage.
        for page in range(1, 5):
            data = fetch(f'https://www.arbeitnow.com/api/job-board-api?page={page}')
            items = data.get('data') or []
            if not items:
                break
            for item in items:
                add(jobs, source='Arbeitnow', identity=item.get('slug'), title=item.get('title'),
                    company=item.get('company_name'), location=item.get('location'),
                    description=item.get('description'), url=item.get('url'), posted=item.get('created_at'))
        sources.append('Arbeitnow')
    except Exception as exc:
        errors.append('Arbeitnow: ' + str(exc))

    try:
        data = fetch('https://remotive.com/api/remote-jobs?limit=1000')
        for item in data.get('jobs', []):
            add(jobs, source='Remotive', identity=item.get('id'), title=item.get('title'),
                company=item.get('company_name'),
                location='Remote · ' + (item.get('candidate_required_location') or 'Worldwide'),
                description=item.get('description'), url=item.get('url'),
                posted=item.get('publication_date'))
        sources.append('Remotive')
    except Exception as exc:
        errors.append('Remotive: ' + str(exc))

    # Configurable employer boards. A token is an exact ATS board identifier;
    # invalid/nonexistent boards are skipped, not reported as live sources.
    config = ROOT / 'boards.json'
    boards = json.loads(config.read_text(encoding='utf-8')) if config.exists() else {}
    for board in boards.get('greenhouse', []):
        company, token = board['company'], board['token']
        try:
            data = fetch(f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true')
            items = data.get('jobs', [])
            for item in items:
                add(jobs, source='Greenhouse · ' + company, identity=item.get('id'),
                    title=item.get('title'), company=company,
                    location=(item.get('location') or {}).get('name', ''),
                    description=item.get('content'), url=item.get('absolute_url'),
                    posted=item.get('first_published') or item.get('updated_at'))
            sources.append('Greenhouse · ' + company)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                errors.append(f'Greenhouse {company}: HTTP {exc.code}')
        except Exception as exc:
            errors.append(f'Greenhouse {company}: {exc}')

    for board in boards.get('lever', []):
        company, token = board['company'], board['token']
        try:
            items = fetch(f'https://api.lever.co/v0/postings/{token}?mode=json')
            for item in items:
                add(jobs, source='Lever · ' + company, identity=item.get('id'),
                    title=item.get('text'), company=company,
                    location=(item.get('categories') or {}).get('location', ''),
                    description=item.get('descriptionPlain') or item.get('description'),
                    url=item.get('hostedUrl') or item.get('applyUrl'),
                    posted=item.get('createdAt'))
            sources.append('Lever · ' + company)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                errors.append(f'Lever {company}: HTTP {exc.code}')
        except Exception as exc:
            errors.append(f'Lever {company}: {exc}')

    unique = {}
    for job in jobs:
        if not relevant(job):
            continue
        job['score'] = rating(job)
        description = job.pop('description')
        job['summary'] = (description[:247].rsplit(' ', 1)[0] + '…') if len(description) > 250 else description
        # Deduplicate across job sources by normalized job URL.
        key = re.sub(r'[?#].*', '', job['url']).rstrip('/').lower()
        unique[key] = job

    # Keep previously found jobs temporarily when feeds are temporarily unavailable.
    if TARGET.exists():
        try:
            previous = json.loads(TARGET.read_text(encoding='utf-8')).get('jobs', [])
            cutoff = (NOW.date() - dt.timedelta(days=21)).isoformat()
            for job in previous:
                if job.get('date', '') >= cutoff and job.get('url'):
                    key = re.sub(r'[?#].*', '', job['url']).rstrip('/').lower()
                    unique.setdefault(key, job)
        except (ValueError, OSError):
            pass

    output = {'updated_at': NOW.isoformat(),
              'jobs': sorted(unique.values(), key=lambda j: (j['date'], j['score']), reverse=True)[:500],
              'sources': sources, 'errors': errors,
              'note': 'Betyg är regelbaserade uppskattningar. Äldre träffar kan vara stängda; kontrollera hos arbetsgivaren.'}
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if not sources and TARGET.exists():
        print('No sources succeeded; preserving previous data:', errors)
        return
    TARGET.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved', len(output['jobs']), 'jobs from', sources, '; errors:', errors)


if __name__ == '__main__':
    main()
