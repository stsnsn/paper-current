"""Cursor-independent collection preview and DOI-safe merge into restored state."""
import argparse
import datetime as dt
from pathlib import Path
import subprocess
import sys
from common import ROOT,load,write,paper_keys,dedupe_records
from topic_filter import annotate


def candidates(rows,inbox,index,cfg):
    used={k for issue in index.get('issues',[]) for k in issue.get('doi_keys',[])}
    for row in inbox:used.update(paper_keys(row))
    decisions=[];added=[]
    for row in dedupe_records(rows):
        row=annotate(row,cfg);keys=paper_keys(row)
        status=('published' if any(keys & set(i.get('doi_keys',[])) for i in index.get('issues',[]))
                else 'queued' if keys & used else 'rejected' if not row['topic_filter']['accepted'] and row['topic_filter']['reason']!='metadata_pending'
                else 'metadata_pending' if not row.get('doi') or not row.get('abstract') or not row.get('title')
                else 'translation_pending')
        decisions.append({'doi':row.get('doi'),'id':row['id'],'status':status,'decision':row['topic_filter'],'discovery':row.get('discovery',[])})
        if status in ('translation_pending','metadata_pending'):
            added.append(row);used.update(keys)
    return added,decisions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--since');p.add_argument('--until');p.add_argument('--request',help='Versioned JSON run request, also supported by Actions push trigger')
    p.add_argument('--routes',default='europepmc,biorxiv');p.add_argument('--journals')
    p.add_argument('--work-dir',default='work/cloud');p.add_argument('--output-dir',default='work/backfill')
    p.add_argument('--apply',action='store_true');a=p.parse_args()
    if a.request:
        request=load(a.request,{})
        for key in ('since','until','routes','journals'):
            if key in request:setattr(a,key,request[key])
        if not isinstance(request.get('apply',False),bool):p.error('request.apply must be boolean')
        a.apply=request.get('apply',False)
    if not a.since or not a.until:p.error('--since and --until, or --request, are required')
    out=Path(a.output_dir);work=Path(a.work_dir);out.mkdir(parents=True,exist_ok=True)
    raw=out/'candidates.json';raw.unlink(missing_ok=True)
    cmd=[sys.executable,str(ROOT/'scripts/collect.py'),'--out',str(raw),'--since',a.since,'--until',a.until,'--routes',a.routes]
    if a.journals:cmd+=['--journals',a.journals]
    result=subprocess.run(cmd)
    cfg=load(ROOT/'config/sources.json');inbox=load(work/'inbox.json',[])
    index=load(ROOT/'docs/data/archive-index.json',{'issues':[]})
    added,decisions=candidates(load(raw,[]),inbox,index,cfg)
    report={'since':a.since,'until':a.until,'routes':a.routes,'journals':a.journals,'collection_exit_code':result.returncode,'applied':False,'additional':len(added),'decisions':decisions}
    if a.apply and result.returncode==0:
        if not (work/'auto-state.json').exists():raise RuntimeError('Restore durable state before applying')
        today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
        for row in added:row['collected_date']=today
        write(work/'inbox.json',dedupe_records(inbox+added));report['applied']=True
    write(out/'backfill-report.json',report)
    print('Backfill:',len(added),'additional; applied:',report['applied'])
    if result.returncode:raise SystemExit(result.returncode)

if __name__=='__main__':main()
