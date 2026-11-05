"""RSS + Europe PMC collector. Keeps all candidates, flags incomplete runs."""
import argparse,datetime as dt,hashlib,json,re,time
import requests,feedparser
from common import ROOT,load,write,text,doi,dedupe_records
from journal_catalog import update_catalog
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',default='work/inbox.json');p.add_argument('--days',type=int);p.add_argument('--reference-dois',help='JSON list of DOIs from a public reference digest');args=p.parse_args()
cfg=load(ROOT/'config/sources.json')
old=load(args.out,[]); records={a['id']:a for a in old};errors=[];counts={}
s=requests.Session();s.headers['User-Agent']='PaperCurrent/0.1 scholarly RSS reader'
def get(url,params=None):
    for n in range(3):
        try:
            r=s.get(url,params=params,timeout=45);r.raise_for_status();return r
        except requests.RequestException:
            if n==2:raise
            time.sleep(2**n)
def relevant(title,abstract):
    t=(title+' '+abstract).lower()
    marine=any(x.lower() in t for x in cfg['marine_terms'])
    genome=any(x.lower() in t for x in cfg['genomics_organism_terms']) and any(x.lower() in t for x in cfg['genomics_method_terms'])
    return ['海洋微生物' if marine else '', '微生物ゲノミクス' if genome else ''] if marine or genome else []
def merge(a,source):
    k=a['id'];before=records.get(k,{})
    # Never replace a valid abstract/translation with missing data.
    if before.get('abstract')==a.get('abstract'):
        for f in ('abstract_ja','title_ja','translation','translation_label'):
            if before.get(f):a[f]=before[f]
    if before.get('title')!=a.get('title'):a.pop('title_ja',None)
    records[k]={**before,**a,'sources':sorted(set(before.get('sources',[])+[source])),'first_seen':before.get('first_seen',dt.date.today().isoformat())}
for url in cfg['feeds']:
    try:
        feed=feedparser.parse(get(url).content)
        if not feed.entries:raise ValueError('RSS has no entries or is not a feed')
        count=0
        for e in feed.entries:
            title=text(e.get('title'));ab=text(e.get('summary',''));tags=[x for x in relevant(title,ab) if x]
            if not tags:continue
            d=next((doi(v) for v in [e.get('prism_doi',''),e.get('dc_identifier',''),e.get('link',''),e.get('id','')] if doi(v)), '')
            k=d or 'rss:'+hashlib.sha256((title+e.get('link','')).encode()).hexdigest()[:20]
            if k not in records:merge(dict(id=k,title=title,abstract='',journal=cfg.get('feed_journals',{}).get(url,''),doi=d,date=e.get('published',''),authors='',tags=tags,license='',license_url='',source_url=e.get('link',''),rights_status='pending'),url)
            else:records[k]['sources']=sorted(set(records[k].get('sources',[])+[url]))
            count+=1
        counts[url]=count
    except Exception as e:errors.append({'source':url,'error':str(e)})
start=(dt.date.today()-dt.timedelta(days=args.days or cfg['lookback_days'])).isoformat();today=dt.date.today().isoformat()
query='('+cfg['europepmc_query']+') AND FIRST_IDATE:['+start+' TO '+today+']'
cursor='*';seen=set();ep='https://www.ebi.ac.uk/europepmc/webservices/rest/search'
try:
    total=0
    while True:
        data=get(ep,dict(query=query,format='json',resultType='core',pageSize=100,cursorMark=cursor)).json()
        batch=data.get('resultList',{}).get('result',[])
        for a in batch:
            d=doi(a.get('doi',''));k=d or 'epmc:'+a['source']+':'+a['id'];ab=text(a.get('abstractText',''));title=text(a.get('title',''))
            tags=[x for x in relevant(title,ab) if x]
            if not tags:continue
            pubtypes=[x.lower() for x in a.get('pubTypeList',{}).get('pubType',[])]
            lic=a.get('license','').lower().strip();by=lic=='cc by'
            merge(dict(id=k,title=title,abstract=ab,journal=a.get('journalInfo',{}).get('journal',{}).get('title',''),doi=d,date=a.get('firstPublicationDate',''),authors=a.get('authorString',''),tags=tags,license='CC BY' if by else a.get('license',''),license_url='https://creativecommons.org/licenses/by/4.0/' if by else '',rights_status='allowed' if by else 'pending',source_url='https://europepmc.org/article/'+a['source']+'/'+a['id'],preprint=a['source']=='PPR',review='review' in pubtypes),'Europe PMC')
        total+=len(batch);nxt=data.get('nextCursorMark')
        if not batch or total>=int(data.get('hitCount',0)):break
        if not nxt or nxt==cursor or nxt in seen:raise RuntimeError('pagination stopped before hitCount was reached')
        seen.add(cursor);cursor=nxt
    counts['Europe PMC']=total
except Exception as e:errors.append({'source':'Europe PMC','error':str(e)})
# bioRxiv is collected explicitly, including new versions and published links.
if cfg.get('biorxiv_enabled',True):
    try:
        cursor=0;total=None
        while total is None or cursor<total:
            data=get(f'https://api.biorxiv.org/details/biorxiv/{start}/{today}/{cursor}').json()
            messages=data.get('messages',[])
            if not messages or 'total' not in messages[0]:raise RuntimeError('Invalid bioRxiv pagination response')
            total=int(messages[0]['total']);batch=data.get('collection',[])
            if not batch and cursor<total:raise RuntimeError('bioRxiv pagination stopped early')
            if not batch:break
            for a in batch:
                title=text(a.get('title',''));ab=text(a.get('abstract',''));tags=[x for x in relevant(title,ab) if x]
                if not tags:continue
                d=doi(a.get('doi'));published=doi(a.get('published'));lic=a.get('license','').lower().replace(' ','-').replace('_','-')
                by=lic in ('cc-by','cc-by-4.0','cc0')
                if not d:continue
                version=str(a.get('version','1'))
                prior=records.get(d,{})
                if int(prior.get('version','0'))>int(version):continue
                merge(dict(id=d,doi=d,title=title,abstract=ab,journal='bioRxiv',preprint=True,
                    version=version,published_doi=published,related_dois=[v for v in (d,published) if v],
                    date=a.get('date',''),authors=a.get('authors',''),tags=tags,
                    license='CC0' if lic=='cc0' else ('CC BY' if by else a.get('license','')),
                    license_url='https://creativecommons.org/publicdomain/zero/1.0/' if lic=='cc0' else ('https://creativecommons.org/licenses/by/4.0/' if by else ''),
                    rights_status='allowed' if by else 'pending',source_url='https://www.biorxiv.org/content/'+d+'v'+version),'bioRxiv')
            cursor+=len(batch)
        counts['bioRxiv']=cursor
        # Known publication metadata makes previously recorded forecasts resolvable.
        for r in list(records.values()):
            if not r.get('preprint') or not r.get('published_doi'):continue
            try:
                pubs=get('https://api.biorxiv.org/pubs/biorxiv/'+r['doi']).json().get('collection',[])
                for pub in pubs:
                    if doi(pub.get('biorxiv_doi'))==r['doi'] and pub.get('published_journal'):
                        r['published_journal']=pub['published_journal'];r['published_doi']=doi(pub.get('published_doi'));break
            except Exception as exc:errors.append({'source':'bioRxiv publication link','error':str(exc)})
    except Exception as exc:errors.append({'source':'bioRxiv','error':str(exc)})
# Optional explicit reference DOI lists bypass relevance filtering.
reference=load(args.reference_dois,[]) if args.reference_dois else []
for d in reference:
    d=doi(d)
    if d and d not in records:records[d]=dict(id=d,doi=d,title='',abstract='',journal='',sources=['reference-digest'],rights_status='pending',tags=[],first_seen=today)
output_records=dedupe_records(list(records.values()))
catalog_path=Path(args.out).parent/'journal-catalog.json'
write(catalog_path,update_catalog(load(catalog_path,[]),output_records,cfg.get('feed_journals',{})))
report={'date':today,'counts':counts,'errors':errors,'stored':len(output_records),'complete':not errors,'reference_total':len(reference),'reference_missing_metadata':[d for d in reference if not records.get(doi(d),{}).get('abstract')]}
write(args.out,output_records);write(str(args.out)+'.report.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
if errors:raise SystemExit(2)
