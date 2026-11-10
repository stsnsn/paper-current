"""RSS + Europe PMC collector. Keeps all candidates, flags incomplete runs."""
import argparse,datetime as dt,hashlib,json,re,time
import requests,feedparser
from concurrent.futures import ThreadPoolExecutor
from topic_scope import scoped_query, field_query, SPECIFIC, bioinformatics_query
from topic_filter import annotate,journal_excluded,watchlist_hits
from rss_records import rss_record,merge_record,normalize_rss_record
from epmc_metadata import enrich_core
from epmc_search import publication_start,discovery_query,recent_publication,watchlist_query
from common import ROOT,load,write,text,doi,dedupe_records
from journal_catalog import update_catalog
from collection_window import source_start
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--watchlist-backfill-since',help='One-time SAR11/Pelagibacter-only publication backfill, YYYY-MM-DD');p.add_argument('--out',default='work/inbox.json');p.add_argument('--days',type=int);p.add_argument('--source-state',help='Automation state with per-source successful collection times');p.add_argument('--source-group');p.add_argument('--journals-only',action='store_true');p.add_argument('--skip-europepmc',action='store_true');p.add_argument('--reference-dois',help='JSON list of DOIs from a public reference digest');p.add_argument('--since');p.add_argument('--until');p.add_argument('--routes',default='rss,europepmc,biorxiv');p.add_argument('--journals',help='Comma separated exact configured journal names');p.add_argument('--progress-file',help='Atomic page checkpoints for resumable backfill');args=p.parse_args()
if bool(args.since)!=bool(args.until):p.error('--since and --until are required together')
if args.since:
    if dt.date.fromisoformat(args.since)>dt.date.fromisoformat(args.until):p.error('Invalid date range')
routes=set(args.routes.split(','))
if routes-{'rss','europepmc','biorxiv'}:p.error('Unknown route')
cfg=load(ROOT/'config/sources.json')
source_state=load(args.source_state,{}) if args.source_state else {}
collection_now=dt.datetime.now(dt.timezone.utc)
def start_for(source):return args.since or source_start(source_state,source,collection_now,args.days or cfg['lookback_days'])
progress=load(args.progress_file,{}) if args.progress_file else {}
source_progress=progress.setdefault('sources',{})
old=progress.get('records',load(args.out,[])); records={a['id']:normalize_rss_record(a) for a in old};errors=[];counts={}
for index,row in enumerate(records.values()):row.setdefault('collection_order',index)
next_collection_order=max((r.get('collection_order',0) for r in records.values()),default=-1)+1
s=requests.Session();s.headers['User-Agent']='PaperCurrent/0.1 scholarly RSS reader'
def get(url,params=None):
    for n in range(3):
        try:
            r=requests.get(url,params=params,headers={'User-Agent':'PaperCurrent/0.4 scholarly RSS reader'},timeout=(5,12) if args.progress_file else (8,25));r.raise_for_status();return r
        except requests.RequestException as exc:
            if isinstance(exc,requests.HTTPError) and exc.response.status_code in (400,401,403,404,410):raise
            if n==2:raise
            time.sleep(2**n)
def relevant(title,abstract,journal='',preprint=False):
    return annotate({'title':title,'abstract':abstract,'journal':journal,'preprint':preprint},cfg)['topic_filter']
def merge(a,source):
    global next_collection_order
    a=annotate(a,cfg)
    prior=records.get(a['id'],{})
    a['collection_order']=prior.get('collection_order',next_collection_order)
    if not prior:next_collection_order+=1
    a['collected_at']=prior.get('collected_at') or ((prior.get('collected_date') or prior.get('first_seen'))+'T00:00:00+09:00' if prior.get('collected_date') or prior.get('first_seen') else collection_now.isoformat())
    a['collected_date']=prior.get('collected_date') or prior.get('first_seen') or collection_now.astimezone(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    if args.watchlist_backfill_since:a['archive_only']=True
    prior=records.get(a['id'],{})
    a['discovery']=prior.get('discovery',[])+[e for e in a.get('discovery',[]) if e not in prior.get('discovery',[])]
    records[a['id']]=annotate(merge_record(prior,a,source),cfg)
def checkpoint():
    # Keep completed sources/pages if a bounded CI run is interrupted later.
    output=list(records.values()) if args.progress_file else [annotate(normalize_rss_record(row),cfg) for row in dedupe_records(list(records.values()))]
    write(args.out,output)
    # Only finished sources advance their cursor, including on a later timeout.
    write(str(args.out)+'.report.json',{'coverage':coverage,'errors':errors,'complete':False})
    write(str(args.out)+'.filter.json',list(filter_decisions.values()))
    if args.progress_file:
        progress.update(records=output,decisions=list(filter_decisions.values()),coverage=coverage,complete=False)
        write(args.progress_file,progress)

def fetch_feed(url):
    try:
        feed=feedparser.parse(get(url).content)
        if not feed.entries:raise ValueError('RSS has no entries or is not a feed')
        return url,feed.entries,None
    except Exception as exc:return url,[],str(exc)
selected_names={name for name,source in cfg.get('source_journals',{}).items() if not journal_excluded(name,cfg) and (not args.source_group or source.get('group')==args.source_group)}
if args.journals:
    requested=set(args.journals.split(','))
    if requested-set(cfg.get('source_journals',{})):p.error('Unknown journal')
    selected_names &= requested
urls=[url for url in cfg['feeds'] if not journal_excluded(cfg.get('feed_journals',{}).get(url,''),cfg) and (not args.journals_only or 'biorxiv' not in url) and (not args.source_group or cfg.get('feed_journals',{}).get(url) in selected_names)]
if args.watchlist_backfill_since or 'rss' not in routes:urls=[]
if args.journals:urls=[u for u in urls if cfg.get('feed_journals',{}).get(u) in selected_names]
filter_counts={'accepted':0,'rejected':0,'metadata_pending':0};coverage=progress.get('coverage',{});filter_decisions={r['id']:r for r in progress.get('decisions',[])};enrichment={'checked':0,'abstracts_recovered':0,'dois_recovered':0,'errors':[]}
def remember_decision(row,source):
    key=row.get('id') or doi(row.get('doi','')) or hashlib.sha256(row.get('title','').encode()).hexdigest()[:20]
    prior=filter_decisions.get(key,{})
    attempt={'source':source,'discovery':row.get('discovery',[]),'decision':row.get('topic_filter') or relevant(row.get('title',''),row.get('abstract',''),row.get('journal',''),row.get('preprint',False))}
    filter_decisions[key]={'attempts':prior.get('attempts',[])+[attempt],'id':key,'doi':doi(row.get('doi') or key),'metadata_status':'ready' if row.get('abstract') and doi(row.get('doi') or key) else 'pending','discovery':row.get('discovery',[]),'title':row.get('title',''),'journal':row.get('journal',''),'sources':sorted(set(prior.get('sources',[])+[source])),'decision':row.get('topic_filter') or relevant(row.get('title',''),row.get('abstract',''),row.get('journal',''),row.get('preprint',False))}
if args.progress_file:urls=[u for u in urls if not coverage.get(u,{}).get('ok')]
with ThreadPoolExecutor(max_workers=8) as pool:
    for url,entries,error in pool.map(fetch_feed,urls):
        journal=cfg.get('feed_journals',{}).get(url,'bioRxiv')
        if error:errors.append({'source':url,'error':error});coverage[url]={'journal':journal,'ok':False};continue
        count=0
        for entry in entries:
            row=rss_record(entry,url,cfg)
            if not row:continue
            if not row.get('date') or row['date']<(args.since or max(start_for(url),publication_start(collection_now,cfg))):continue
            if args.until and row['date']>args.until:continue
            row['discovery']=[{'source':url,'query':'RSS feed','scope':'journal' if cfg.get('source_journals',{}).get(journal,{}).get('filter')=='none' else 'candidate'}]
            remember_decision(row,url)
            decision=row['topic_filter'];filter_counts['accepted' if decision['accepted'] else 'metadata_pending' if decision['reason']=='metadata_pending' else 'rejected']+=1
            if not decision['accepted'] and decision['reason']!='metadata_pending':continue
            # Retain complete source metadata. Public eligibility is checked later.
            merge(row,url);count+=1
        counts[url]=count;coverage[url]={'journal':journal,'ok':True,'entries':len(entries),'accepted':count}
        checkpoint()
        print('RSS:',journal,count,'accepted /',len(entries),'entries',flush=True)
checkpoint()
today=args.until or collection_now.date().isoformat()
queries=[]
if cfg.get('europepmc_watchlist') and not args.journals:queries.append(('Europe PMC watchlist',watchlist_query(cfg)))
if not args.journals_only and not args.journals:
    queries.append(('Europe PMC topics','('+scoped_query(cfg)+')'))
    queries.append(('Europe PMC genome methods',field_query(SPECIFIC)))
    queries.append(('Europe PMC bioinformatics',bioinformatics_query()))
if cfg.get('europepmc_journal_queries',True):
    names=[name for name in cfg.get('source_journals',{}) if name in selected_names]
    for offset in range(0,len(names),8):
        group=names[offset:offset+8]
        queries.append(('Europe PMC journals '+str(offset//8+1),'('+' OR '.join('JOURNAL:"'+name+'"' for name in group)+')'))
if args.watchlist_backfill_since:queries=[('Europe PMC SAR11 backfill',watchlist_query({'europepmc_watchlist':['SAR11','Pelagibacter']}))]
if 'europepmc' not in routes or args.skip_europepmc or not cfg.get('europepmc_enabled',True):queries=[]
ep='https://www.ebi.ac.uk/europepmc/webservices/rest/search'
for source,base_query in queries:
    published_since=args.since or args.watchlist_backfill_since or publication_start(collection_now,cfg)
    query=discovery_query(base_query,('1900-01-01' if args.watchlist_backfill_since else start_for(source)),today,published_since,args.journals_only)
    if args.since:query=base_query+' AND FIRST_PDATE:['+args.since+' TO '+args.until+']'+(' NOT SRC:PPR' if args.journals_only else '')
    previous=source_progress.get(source,{}) if args.progress_file else {}
    if previous.get('query')!=query:previous={}
    if previous.get('done'):
        counts[source]=previous['retrieved']
        print(source,': resumed completed source',previous['retrieved'],flush=True)
        continue
    cursor=previous.get('cursor','*');seen=set();total=previous.get('retrieved',0);accepted=previous.get('accepted',0)
    try:
        while True:
            data=get(ep,dict(query=query,format='json',resultType='core',pageSize=5 if args.progress_file else 50,cursorMark=cursor)).json()
            batch=data.get('resultList',{}).get('result',[])
            for a in batch:
                if source not in ('Europe PMC watchlist','Europe PMC SAR11 backfill') and journal_excluded(a.get('journalInfo',{}).get('journal',{}).get('title',''),cfg):continue
                if (not a.get('abstractText') or not a.get('doi')) and (a.get('pmcid') or a.get('source')=='PMC'):
                    enrichment['checked']+=1;original=a
                    try:
                        a=enrich_core(a,get,Path(args.out).parent/'cache/europepmc')
                        enrichment['abstracts_recovered']+=int(not original.get('abstractText') and bool(a.get('abstractText')))
                        enrichment['dois_recovered']+=int(not original.get('doi') and bool(a.get('doi')))
                    except Exception as exc:enrichment['errors'].append({'source':a.get('source'),'id':a.get('id'),'error':str(exc)})
                if not recent_publication(a,published_since,today):continue
                d=doi(a.get('doi',''));key=d or 'epmc:'+a['source']+':'+a['id'];ab=text(a.get('abstractText',''));title=text(a.get('title',''))
                journal=a.get('journalInfo',{}).get('journal',{}).get('title','');preprint=a['source']=='PPR'
                if source=='Europe PMC watchlist' and not watchlist_hits({'title':title,'abstract':ab},cfg):continue
                pubtypes=[x.lower() for x in a.get('pubTypeList',{}).get('pubType',[])]
                evidence=[{'source':source,'query':query,'scope':'target' if source=='Europe PMC topics' or 'watchlist' in source or 'SAR11 backfill' in source else 'candidate'}]
                decision=annotate({'title':title,'abstract':ab,'journal':journal,'preprint':preprint,'discovery':evidence,'publication_types':pubtypes},cfg)['topic_filter']
                remember_decision({'id':key,'title':title,'abstract':ab,'journal':journal,'preprint':preprint,'discovery':evidence,'topic_filter':decision},source)
                filter_counts['accepted' if decision['accepted'] else 'metadata_pending' if decision['reason']=='metadata_pending' else 'rejected']+=1
                if not decision['accepted'] and decision['reason']!='metadata_pending':continue
                pubtypes=[x.lower() for x in a.get('pubTypeList',{}).get('pubType',[])]
                merge(dict(discovery=evidence,publication_types=pubtypes,id=key,title=title,abstract=ab,journal=journal,doi=d,date=a.get('firstPublicationDate',''),authors=a.get('authorString',''),tags=decision['tags'],source_url='https://europepmc.org/article/'+a['source']+'/'+a['id'],preprint=preprint,review='review' in pubtypes,pmcid=a.get('pmcid',''),pmid=a.get('pmid') or (a['id'] if a['source']=='MED' else ''),metadata_source_url=a.get('metadata_source_url',''),abstract_source=a.get('abstract_source','Europe PMC')),source)
                accepted+=1
            total+=len(batch);nxt=data.get('nextCursorMark')
            done=not batch or total>=int(data.get('hitCount',0))
            if not done and (not nxt or nxt==cursor or nxt in seen):raise RuntimeError('pagination stopped before hitCount was reached')
            source_progress[source]={'query':query,'cursor':nxt,'retrieved':total,'accepted':accepted,'done':done}
            coverage[source]={'ok':done,'retrieved':total,'accepted':accepted,'query':query,'publication_start':published_since}
            checkpoint()
            print(source,': checkpoint',total,'/',data.get('hitCount',0),flush=True)
            if done:break
            seen.add(cursor);cursor=nxt
        counts[source]=total;coverage[source]={'ok':True,'retrieved':total,'accepted':accepted,'query':query,'publication_start':published_since}
        print(source,':',accepted,'accepted /',total,'records',flush=True)
    except Exception as exc:
        errors.append({'source':source,'error':str(exc)});coverage[source]={'ok':False,'retrieved':total,'query':query,'publication_start':published_since}
        if args.progress_file and cursor!='*' and isinstance(exc,requests.HTTPError) and exc.response is not None and exc.response.status_code==400:
            source_progress.pop(source,None)  # Expired cursor: retry only this query, DOI candidates remain safe.
    checkpoint()
# bioRxiv is collected explicitly, including new versions and published links.
if 'biorxiv' in routes and not args.journals and cfg.get('biorxiv_enabled',True) and not args.journals_only and not args.watchlist_backfill_since:
    try:
        start=args.since or max(start_for('bioRxiv'),publication_start(collection_now,cfg))
        biorxiv_query=f'details/biorxiv/{start}/{today}'
        previous=source_progress.get('bioRxiv',{}) if args.progress_file else {}
        if previous.get('query')!=biorxiv_query:previous={}
        cursor=previous.get('cursor',0);total=previous.get('total')
        while total is None or cursor<total:
            data=get(f'https://api.biorxiv.org/details/biorxiv/{start}/{today}/{cursor}').json()
            messages=data.get('messages',[])
            if not messages or 'total' not in messages[0]:raise RuntimeError('Invalid bioRxiv pagination response')
            total=int(messages[0]['total']);batch=data.get('collection',[])
            if not batch and cursor<total:raise RuntimeError('bioRxiv pagination stopped early')
            if not batch:break
            for a in batch:
                title=text(a.get('title',''));ab=text(a.get('abstract',''));decision=relevant(title,ab,preprint=True)
                evidence=[{'source':'bioRxiv','query':f'details/biorxiv/{start}/{today}','scope':'candidate'}]
                remember_decision({'id':doi(a.get('doi')),'title':title,'abstract':ab,'journal':'bioRxiv','preprint':True,'discovery':evidence,'topic_filter':decision},'bioRxiv')
                filter_counts['accepted' if decision['accepted'] else 'metadata_pending' if decision['reason']=='metadata_pending' else 'rejected']+=1
                if not decision['accepted'] and decision['reason']!='metadata_pending':continue
                tags=decision['tags']
                d=doi(a.get('doi'));published=doi(a.get('published'))
                if not d:continue
                version=str(a.get('version','1'))
                prior=records.get(d,{})
                if int(prior.get('version','0'))>int(version):continue
                merge(dict(discovery=evidence,id=d,doi=d,title=title,abstract=ab,journal='bioRxiv',preprint=True,
                    version=version,published_doi=published,related_dois=[v for v in (d,published) if v],
                    date=a.get('date',''),authors=a.get('authors',''),tags=tags,
                    source_url='https://www.biorxiv.org/content/'+d+'v'+version),'bioRxiv')
            cursor+=len(batch)
            source_progress['bioRxiv']={'query':biorxiv_query,'cursor':cursor,'total':total,'retrieved':cursor,'done':cursor>=total}
            coverage['bioRxiv']={'ok':cursor>=total,'retrieved':cursor,'query':biorxiv_query}
            checkpoint()
            print('bioRxiv: checkpoint',cursor,'/',total,flush=True)
        counts['bioRxiv']=cursor
        coverage['bioRxiv']={'ok':True,'retrieved':cursor,'query':f'details/biorxiv/{start}/{today}'}
        checkpoint()
        # Known publication metadata makes previously recorded forecasts resolvable.
        for r in list(records.values()):
            if args.progress_file or not r.get('preprint') or not r.get('published_doi'):continue
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
    if d and d not in records:records[d]=dict(id=d,doi=d,title='',abstract='',journal='',sources=['reference-digest'],tags=[],first_seen=today)
output_records=[annotate(normalize_rss_record(row),cfg) for row in dedupe_records(list(records.values()))]
write(str(args.out)+'.filter.json',list(filter_decisions.values()))
catalog_path=Path(args.out).parent/'journal-catalog.json'
write(catalog_path,update_catalog(load(catalog_path,[]),output_records,cfg.get('feed_journals',{})))
report={'date':today,'window':{'since':args.since,'until':args.until,'routes':sorted(routes)},'filter_version':cfg.get('filtering',{}).get('version'),'excluded_journals':cfg.get('excluded_journals',[]),'frontiers_allowed_journals':cfg.get('frontiers_allowed_journals',[]),'counts':counts,'errors':errors,'stored':len(output_records),'complete':not errors,'coverage':coverage,'filter_counts':filter_counts,'metadata_enrichment':enrichment,'reference_total':len(reference),'reference_missing_metadata':[d for d in reference if not records.get(doi(d),{}).get('abstract')]}
write(args.out,output_records);write(str(args.out)+'.report.json',report)
if args.progress_file:
    progress.update(records=output_records,decisions=list(filter_decisions.values()),coverage=coverage,complete=not errors)
    write(args.progress_file,progress)
print(json.dumps(report,ensure_ascii=False,indent=2))
if errors:raise SystemExit(2)
