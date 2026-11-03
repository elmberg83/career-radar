import json
import re
import urllib.request
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOW = datetime.datetime.now(datetime.timezone.utc)
KEYWORDS = ['account manager', 'account director', 'customer success', 'business development', 'commercial manager', 'commercial director', 'sales director', 'head of sales', 'vp sales', 'partnership', 'client relationship', 'customer engagement', 'regional sales', 'key account', 'sales manager']
PREFERRED = ['maritime', 'shipping', 'marine', 'energy', 'sustainability', 'industrial', 'saas', 'technology', 'decarbon', 'logistics']
PLACES = ['denmark', 'copenhagen', 'københavn', 'hellerup', 'lyngby', 'sjælland', 'zealand', 'sweden', 'malmö', 'malmo', 'lund', 'skåne', 'skane', 'remote', 'europe', 'emea', 'worldwide']


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'CareerRadar/1.0 (public job feed reader)'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def strip(value):
    return re.sub(r'<[^>]+>', ' ', value or '').replace('&amp;', '&').strip()


def score(job):
    title = job['title'].lower()
    body = (job['description'] + ' ' + job['company']).lower()
    location = job['location'].lower()
    value = 5.0
    if any(term in title for term in ['customer success', 'strategic account', 'key account', 'account director', 'commercial manager', 'commercial director', 'partnership']):
        value += 2.1
    elif any(term in title for term in ['business development', 'head of sales', 'sales director', 'vp sales']):
        value += 1.5
    else:
        value += 0.8
    if any(term in body for term in PREFERRED):
        value += 1.0
    if any(term in location for term in ['copenhagen', 'denmark', 'malmö', 'malmo', 'lund', 'sweden']):
        value += 0.7
    if 'remote' in location:
        value += 0.3
    if any(term in body for term in ['cold calling', 'door-to-door', 'commission only']):
        value -= 1.0
    return round(min(10, max(1, value)), 1)


def eligible(job):
    title = job['title'].lower()
    location = job['location'].lower()
    return any(term in title for term in KEYWORDS) and any(term in location for term in PLACES)


def main():
    jobs = []
    errors = []
    try:
        data = fetch('https://www.arbeitnow.com/api/job-board-api')
        for item in data.get('data', []):
            jobs.append({
                'id': 'arbeitnow:' + str(item.get('slug')),
                'title': item.get('title') or '',
                'company': item.get('company_name') or '',
                'location': item.get('location') or '',
                'description': strip(item.get('description'))[:900],
                'url': item.get('url') or '',
                'date': datetime.datetime.fromtimestamp(item.get('created_at') or NOW.timestamp(), datetime.timezone.utc).date().isoformat(),
                'source': 'Arbeitnow',
            })
    except Exception as exc:
        errors.append('Arbeitnow: ' + str(exc))

    try:
        data = fetch('https://remotive.com/api/remote-jobs?limit=1000')
        for item in data.get('jobs', []):
            jobs.append({
                'id': 'remotive:' + str(item.get('id')),
                'title': item.get('title') or '',
                'company': item.get('company_name') or '',
                'location': 'Remote · ' + (item.get('candidate_required_location') or 'Worldwide'),
                'description': strip(item.get('description'))[:900],
                'url': item.get('url') or '',
                'date': (item.get('publication_date') or '')[:10],
                'source': 'Remotive',
            })
    except Exception as exc:
        errors.append('Remotive: ' + str(exc))

    unique = {}
    for job in jobs:
        if eligible(job) and job['url']:
            job['score'] = score(job)
            description = job['description']
            job['summary'] = (description[:250].rsplit(' ', 1)[0] + '…') if len(description) > 250 else description
            job.pop('description', None)
            unique[job['id']] = job

    output = {
        'updated_at': NOW.isoformat(),
        'jobs': sorted(unique.values(), key=lambda job: (job['date'], job['score']), reverse=True)[:250],
        'sources': ['Arbeitnow', 'Remotive'],
        'errors': errors,
        'note': 'Betyg är heuristiska och preliminära; annonser och tillgänglighet måste kontrolleras hos arbetsgivaren.',
    }
    target = ROOT / 'data' / 'jobs.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if errors and not jobs and target.exists():
        print('All feeds failed; preserving last successful data:', errors)
        return
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved', len(output['jobs']), 'jobs', errors)


if __name__ == '__main__':
    main()
