import json, re, urllib.request, datetime, pathlib
ROOT=pathlib.Path(__file__).parent
NOW=datetime.datetime.now(datetime.timezone.utc)
KEYWORDS=['account manager','account director','customer success','business development','commercial manager','commercial director','sales director','head of sales','vp sales','partnership','client relationship','customer engagement','regional sales','key account','sales manager']
PREFERRED=['maritime','shipping','marine','energy','sustainability','industrial','saas','technology','decarbon','logistics']
PLACES=['denmark','copenhagen','københavn','hellerup','lyngby','sjælland','zealand','sweden','malmö','malmo','lund','skåne','skane','remote','europe','emea','worldwide']
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'CareerRadar/1.0 (public job feed reader)'})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def strip(s):return re.sub(r'<[^>]+>',' ',s or '').replace('&amp;','&').strip()
def score(job):
 t=job['title'].lower(); body=(job['description']+' '+job['company']).lower(); location=job['location'].lower()
 v=5.0
 if any(x in t for x in ['customer success','strategic account','key account','account director','commercial manager','commercial director','partnership']):v+=2.1
 elif any(x in t for x in ['business development','head of sales','sales director','vp sales']):v+=1.5
 else:v+=0.8
 if any(x in body for x in PREFERRED):v+=1.0
 if any(x in location for x in ['copenhagen','denmark','malmö','malmo','lund','sweden']):v+=0.7
 if 'remote' in location:v+=0.3
 if any(x in body for x in ['cold calling','door-to-door','commission only']):v-=1.0
 return round(min(10,max(1,v)),1)
def eligible(j):
 title=j['title'].lower(); loc=j['location'].lower()
 return any(x in title for x in KEYWORDS) and any(x in loc for x in PLACES)
def main():
 jobs=[]; errors=[]
 try:
  data=fetch('https://www.arbeitnow.com/api/job-board-api')
  for x in data.get('data',[]):
   jobs.append(dict(id='arbeitnow:'+str(x.get('slug')),title=x.get('title',''),company=x.get('company_name',''),location=x.get('location',''),description=strip(x.get('description',''))[:900],url=x.get('url',''),date=datetime.datetime.fromtimestamp(x.get('created_at') or NOW.timestamp(),datetime.timezone.utc).date().isoformat(),source='Arbeitnow'))
 except Exception as e:errors.append('Arbeitnow: '+str(e))
 try:
  data=fetch('https://remotive.com/api/remote-jobs?limit=1000')
  for x in data.get('jobs',[]):
   jobs.append(dict(id='remotive:'+str(x.get('id')),title=x.get('title',''),company=x.get('company_name',''),location='Remote · '+x.get('candidate_required_location','Worldwide'),description=strip(x.get('description',''))[:900],url=x.get('url',''),date=(x.get('publication_date') or '')[:10],source='Remotive'))
 except Exception as e:errors.append('Remotive: '+str(e))
 unique={}
 for j in jobs:
  if eligible(j) and j['url']:
   j['score']=score(j)
   j['summary']=j['description'][:250].rsplit(' ',1)[0]+'…' if len(j['description'])>250 else j['description']
   j.pop('description',None)
   unique[j['id']]=j
 output = {
        'updated_at': NOW.isoformat(),
        'jobs': sorted(
            unique.values(),
            key=lambda j: (j['date'], j['score']),
            reverse=True
        )[:250],
        'sources': ['Arbeitnow', 'Remotive'],
        'errors': errors,
        'note': 'Betyg är heuristiska och preliminära; annonser och tillgänglighet måste kontrolleras hos arbetsgivaren.'
    }

    target = ROOT / 'data/jobs.json'
    target.parent.mkdir(parents=True, exist_ok=True)

    if errors and not jobs and target.exists():
        print('All feeds failed; preserving last successful data:', errors)
        return

    target.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8'
    )
    print('Saved', len(output['jobs']), 'jobs', errors)


if __name__ == '__main__':
    main()
