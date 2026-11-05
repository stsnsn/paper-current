"""Resume local PLaMo translation: journals first, then relevant bioRxiv.
Keeps raw and excluded records, and never builds, publishes, or pushes an issue.
"""
import argparse,datetime as dt,json
from collections import defaultdict,deque
from pathlib import Path
from common import ROOT,load,write,dedupe_records
from topic_filter import annotate
from translate import Translator,translate_records,fingerprint
from auto import worker_lock

def ordered_groups(rows):
    groups=defaultdict(deque)
    for row in sorted(rows,key=lambda a:a.get('date',''),reverse=True):groups[row.get('journal','')].append(row)
    ordered=[]
    while any(groups.values()):
        for name in sorted(groups,key=str.casefold):
            if groups[name]:ordered.append(groups[name].popleft())
    return ordered

def is_complete(row,previous,model):
    old=previous.get(row['id'],{})
    return all(old.get(field+'_ja') and old.get('translation',{}).get(field,{}).get('hash')==fingerprint(row[field],model)
               for field in ('title','abstract') if row.get(field))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work-dir',default=str(ROOT/'work'))
    p.add_argument('--batch-size',type=int,default=20);p.add_argument('--include-pending',action='store_true')
    args=p.parse_args();work=Path(args.work_dir);cfg=load(ROOT/'config/automation.json');sources=load(ROOT/'config/sources.json')
    if args.batch_size<1:p.error('batch-size must be positive')
    with worker_lock(work/'auto.lock'):
        translator=Translator(cfg['base_url'],cfg.get('model'),cfg['max_tokens']).connect()
        rows=[annotate(row,sources) for row in dedupe_records(load(work/'inbox.json',[]))]
        write(work/'inbox.json',rows)
        permitted=lambda r:r.get('rights_status')=='allowed' or (args.include_pending and r.get('rights_status')=='pending')
        selected=[r for r in rows if r.get('title') and permitted(r) and r['topic_filter']['accepted']]
        stages=[('journals',ordered_groups([r for r in selected if not r.get('preprint')])),
                ('biorxiv',ordered_groups([r for r in selected if r.get('preprint')]))]
        for stage,queue in stages:
            print('Stage:',stage,'records:',len(queue),flush=True)
            while True:
                previous={r['id']:r for r in load(work/'translated.json',[])}
                pending=[r for r in queue if not is_complete(r,previous,translator.model)]
                status={'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'phase':stage,'model':translator.model,
                    'selected':len(selected),'excluded_by_topic':sum(not r['topic_filter']['accepted'] for r in rows),
                    'stages':{name:{'total':len(items),'complete':sum(is_complete(r,previous,translator.model) for r in items)} for name,items in stages}}
                write(work/'translation-status.json',status)
                if not pending:break
                stats=translate_records(pending,work/'translated.json',translator,limit=args.batch_size,keep_going=True,
                    retry_state=work/'translation-retries.json',include_pending=args.include_pending)
                print(stage,json.dumps(stats),flush=True)
                if not stats['translated']:
                    # Preserve strict journal priority even if an upstream failure blocks it.
                    status['phase']='needs_retry';status['blocked_stage']=stage
                    write(work/'translation-status.json',status);return 2
        status['phase']='complete';status['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat();write(work/'translation-status.json',status)
        return 0
if __name__=='__main__':raise SystemExit(main())
