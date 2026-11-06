"""RSS + Europe PMC collector. Keeps all candidates, flags incomplete runs."""
import argparse,datetime as dt,hashlib,json,re,time
import requests,feedparser
from concurrent.futures import ThreadPoolExecutor
from topic_filter import annotate
from rss_records import rss_record,merge_record,normalize_rss_record
from epmc_metadata import enrich_core
from common import ROOT,load,write,text,doi,dedupe_records
from journal_catalog import update_catalog
from collection_window import source_start
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',default='work/inbox.json');p.add_argument('--days',type=int);p.add_argument('--source-state',help='Automation state with per-source successful collection times');p.add_argument('--source-group');p.add_argument('--journals-only',action='store_true');p.add_argument('--skip-europepmc',action='store_true');p.add_argument('--reference-dois',help='JSON list of DOIs from a public reference digest');args=p.parse_args()
cfg=load(ROOT/'config/sources.json')
source_state=load(args.source_state,{}) if args.source_state else {}
collection_now=dt.datetime.now(dt.timezone.utc)
def start_for(source):return source_start(source_state,source,collection_now,args.days or cfg['lookback_days'])
old=load(args.out,[]); records={a['id']:normalize_rss_record(a) for a in old};errors=[];counts={}
s=requests.Session();s.headers['User-Agent']='PaperCurrent/0.1 scholarly RSS reader'
def get(url,params=None):
    for n in range(3):
        try:
            r=requests.get(url,params=params,headers={'User-Agent':'PaperCurrent/0.4 scholarly RSS reader'},timeout=(8,25));r.raise_for_status();return r
        except requests.RequestException as exc:
            if isinstance(exc,requests.HTTPError) and exc.response.status_code in (400,401,403,404,410):raise
            if n==2:raise
            time.sleep(2**n)
def relevant(title,abstract,journal='',preprint=False):
    return annotate({'title':title,'abstract':abstract,'journal':journal,'preprint':preprint},cfg)['topic_filter']
def merge(a,source):
    a=annotate(a,cfg);records[a['id']]=merge_record(records.get(a['id'],{}),a,source)
def checkpoint():
    # Keep completed sources/pages if a bounded CI run is interrupted later.
    write(args.out,[annotate(normalize_rss_record(row),cfg) for row in dedupe_records(list(records.values()))])
    # Only finished sources advance their cursor, including on a later timeout.
    write(str(args.out)+'.report.json',{'coverage':coverage,'errors':errors,'complete':False})

def fetch_feed(url):
    try:
        feed=feedparser.parse(get(url).content)
        if not feed.entries:raise ValueError('RSS has no entries or is not a feed')
        return url,feed.entries,None
    except Exception as exc:return url,[],str(exc)
selected_names={name for name,source in cfg.get('source_journals',{}).items() if not args.source_group or source.get('group')==args.source_group}
urls=[url for url in cfg['feeds'] if (not args.journals_only or 'biorxiv' not in url) and (not args.source_group or cfg.get('feed_journals',{}).get(url) in selected_names)]
filter_counts={'accepted':0,'rejected':0};coverage={};filter_decisions={};enrichment={'checked':0,'abstracts_recovered':0,'dois_recovered':0,'errors':[]}
def remember_decision(row,source):
    key=row.get('id') or doi(row.get('doi','')) or hashlib.sha256(row.get('title','').encode()).hexdigest()[:20]
    prior=filter_decisions.get(key,{})
    filter_decisions[key]={'id':key,'title':row.get('title',''),'journal':row.get('journal',''),'sources':sorted(set(prior.get('sources',[])+[source])),'decision':row.get('topic_filter') or relevant(row.get('title',''),row.get('abstract',''),row.get('journal',''),row.get('preprint',False))}
with ThreadPoolExecutor(max_workers=8) as pool:
    for url,entries,error in pool.map(fetch_feed,urls):
        journal=cfg.get('feed_journals',{}).get(url,'bioRxiv')
        if error:errors.append({'source':url,'error':error});coverage[url]={'journal':journal,'ok':False};continue
        count=0
        for entry in entries:
            row=rss_record(entry,url,cfg)
            if not row:continue
            if row.get('date') and row['date']<start_for(url):continue
            remember_decision(row,url)
            decision=row['topic_filter'];filter_counts['accepted' if decision['accepted'] else 'rejected']+=1
            if not decision['accepted']:continue
            # Retain complete source metadata. Public eligibility is checked later.
            merge(row,url);count+=1
        counts[url]=count;coverage[url]={'journal':journal,'ok':True,'entries':len(entries),'accepted':count}
        checkpoint()
        print('RSS:',journal,count,'accepted /',len(entries),'entries',flush=True)
checkpoint()
today=collection_now.date().isoformat()
queries=[]
if not args.journals_only:queries.append(('Europe PMC topics','('+cfg['europepmc_query']+')'))
if cfg.get('europepmc_journal_queries',True):
    names=[name for name in cfg.get('source_journals',{}) if name in selected_names]
    for offset in range(0,len(names),8):
        group=names[offset:offset+8]
        queries.append(('Europe PMC journals '+str(offset//8+1),'('+' OR '.join('JOURNAL:"'+name+'"' for name in group)+')'))
if args.skip_europepmc or not cfg.get('europepmc_enabled',True):queries=[]
ep='https://www.ebi.ac.uk/europepmc/webservices/rest/search'
for source,base_query in queries:
    query=base_query+' AND FIRST_IDATE:['+start_for(source)+' TO '+today+']'+(' NOT SRC:PPR' if args.journals_only else '')
    cursor='*';seen=set();total=0;accepted=0
    try:
        while True:
            data=get(ep,dict(query=query,format='json',resultType='core',pageSize=50,cursorMark=cursor)).json()
            batch=data.get('resultList',{}).get('result',[])
            for a in batch:
                if (not a.get('abstractText') or not a.get('doi')) and (a.get('pmcid') or a.get('source')=='PMC'):
                    enrichment['checked']+=1;original=a
                    try:
                        a=enrich_core(a,get,Path(args.out).parent/'cache/europepmc')
                        enrichment['abstracts_recovered']+=int(not original.get('abstractText') and bool(a.get('abstractText')))
                        enrichment['dois_recovered']+=int(not original.get('doi') and bool(a.get('doi')))
                    except Exception as exc:enrichment['errors'].append({'source':a.get('source'),'id':a.get('id'),'error':str(exc)})
                d=doi(a.get('doi',''));key=d or 'epmc:'+a['source']+':'+a['id'];ab=text(a.get('abstractText',''));title=text(a.get('title',''))
                journal=a.get('journalInfo',{}).get('journal',{}).get('title','');preprint=a['source']=='PPR'
                decision=relevant(title,ab,journal,preprint)
                remember_decision({'id':key,'title':title,'abstract':ab,'journal':journal,'preprint':preprint,'topic_filter':decision},source)
                filter_counts['accepted' if decision['accepted'] else 'rejected']+=1
                if not decision['accepted']:continue
                pubtypes=[x.lower() for x in a.get('pubTypeList',{}).get('pubType',[])]
                lic=a.get('license','').lower().strip();by=lic=='cc by'
                merge(dict(id=key,title=title,abstract=ab,journal=journal,doi=d,date=a.get('firstPublicationDate',''),authors=a.get('authorString',''),tags=decision['tags'],license='CC BY' if by else a.get('license',''),license_url='https://creativecommons.org/licenses/by/4.0/' if by else '',rights_status='allowed' if by else 'pending',source_url='https://europepmc.org/article/'+a['source']+'/'+a['id'],preprint=preprint,review='review' in pubtypes,pmcid=a.get('pmcid',''),pmid=a.get('pmid') or (a['id'] if a['source']=='MED' else ''),metadata_source_url=a.get('metadata_source_url',''),abstract_source=a.get('abstract_source','Europe PMC')),source)
                accepted+=1
            checkpoint()
            total+=len(batch);nxt=data.get('nextCursorMark')
            if not batch or total>=int(data.get('hitCount',0)):break
            if not nxt or nxt==cursor or nxt in seen:raise RuntimeError('pagination stopped before hitCount was reached')
            seen.add(cursor);cursor=nxt
        counts[source]=total;coverage[source]={'ok':True,'retrieved':total,'accepted':accepted}
        print(source,':',accepted,'accepted /',total,'records',flush=True)
    except Exception as exc:errors.append({'source':source,'error':str(exc)});coverage[source]={'ok':False,'retrieved':total}
    checkpoint()
# bioRxiv is collected explicitly, including new versions and published links.
if cfg.get('biorxiv_enabled',True) and not args.journals_only:
    try:
        start=start_for('bioRxiv')
        cursor=0;total=None
        while total is None or cursor<total:
            data=get(f'https://api.biorxiv.org/details/biorxiv/{start}/{today}/{cursor}').json()
            messages=data.get('messages',[])
            if not messages or 'total' not in messages[0]:raise RuntimeError('Invalid bioRxiv pagination response')
            total=int(messages[0]['total']);batch=data.get('collection',[])
            if not batch and cursor<total:raise RuntimeError('bioRxiv pagination stopped early')
            if not batch:break
            for a in batch:
                title=text(a.get('title',''));ab=text(a.get('abstract',''));decision=relevant(title,ab,preprint=True)
                remember_decision({'id':doi(a.get('doi')),'title':title,'abstract':ab,'journal':'bioRxiv','preprint':True,'topic_filter':decision},'bioRxiv')
                filter_counts['accepted' if decision['accepted'] else 'rejected']+=1
                if not decision['accepted']:continue
                tags=decision['tags']
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
            checkpoint()
            cursor+=len(batch)
        counts['bioRxiv']=cursor
        coverage['bioRxiv']={'ok':True,'retrieved':cursor}
        checkpoint()
        # Known publication metadata makes previously recorded forecasts resolvable.
        for r in list(records.values()):
            if not r.get('preprint') or not r.get('published_doi'):continue
            try:
                pubs=get('https://api.biorxiv.org/pubs/biorxiv/'+r['doi']).json().get('collection',[])
                for pub in pubs:
                    if doi(pub.get('biorxiv_doi'))==r['doi'] and pub.get('published_journal'):
                        r['published_journal']=pub['published_journal'];r['published_doi']=doi(pub.get('published_doi'));break
            except Exception as exc:errors.append({'source':'bioRxiv publication link','error':str(exc)})
    except Exception as exc:errors.append({'source':'bioRxiv','error':str(exc)});coverage['bioRxiv']={'ok':False}
# Optional explicit reference DOI lists bypass relevance filtering.
reference=load(args.reference_dois,[]) if args.reference_dois else []
for d in reference:
    d=doi(d)
    if d and d not in records:records[d]=dict(id=d,doi=d,title='',abstract='',journal='',sources=['reference-digest'],rights_status='pending',tags=[],first_seen=today)
output_records=[annotate(normalize_rss_record(row),cfg) for row in dedupe_records(list(records.values()))]
write(str(args.out)+'.filter.json',list(filter_decisions.values()))
catalog_path=Path(args.out).parent/'journal-catalog.json'
write(catalog_path,update_catalog(load(catalog_path,[]),output_records,cfg.get('feed_journals',{})))
report={'date':today,'counts':counts,'errors':errors,'stored':len(output_records),'complete':not errors,'coverage':coverage,'filter_counts':filter_counts,'metadata_enrichment':enrichment,'reference_total':len(reference),'reference_missing_metadata':[d for d in reference if not records.get(doi(d),{}).get('abstract')]}
write(args.out,output_records);write(str(args.out)+'.report.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
if errors:raise SystemExit(2)
