"""Cursor-independent collection preview and DOI-safe merge into restored state."""
import argparse
import datetime as dt
import hashlib
from pathlib import Path
import subprocess
import sys
from common import ROOT,load,write,paper_keys,dedupe_records
from topic_filter import annotate
from process_control import run_bounded


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


def run_backfill(since,until,routes,journals,work,out,apply=False,incremental=False,budget_seconds=600,request_id=None):
    work=Path(work);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=out/'candidates.json'
    progress_path=work/'backfill-progress.json'
    if incremental:
        # A cursor is valid only for the same request, query rules and collector code.
        signature=hashlib.sha256(json_bytes({'id':request_id,'since':since,'until':until,'routes':routes,'journals':journals,
                    'config':load(ROOT/'config/sources.json'),
                    'scope':(ROOT/'scripts/topic_scope.py').read_text(),
                    'collector':hashlib.sha256((ROOT/'scripts/collect.py').read_bytes()).hexdigest()})).hexdigest()
        progress=load(progress_path,{})
        if progress.get('signature')!=signature:
            progress={'signature':signature,'request_id':request_id,'sources':{},'records':[],'decisions':[]}
            write(progress_path,progress)
        write(raw,progress.get('records',[]))
    else:raw.unlink(missing_ok=True)
    cmd=[sys.executable,str(ROOT/'scripts/collect.py'),'--out',str(raw),'--since',since,'--until',until,'--routes',routes]
    if journals:cmd+=['--journals',journals]
    if incremental:
        cmd+=['--progress-file',str(progress_path)]
        code,timed_out=run_bounded(cmd,budget_seconds)
        progress=load(progress_path,{})
        # Only the atomic snapshot pairs candidate data with a committed cursor.
        rows=progress.get('records',[])
        write(raw,rows);write(str(raw)+'.filter.json',progress.get('decisions',[]))
        complete=code==0 and bool(progress.get('complete'))
        coverage=progress.get('coverage',{})
    else:
        code=subprocess.run(cmd).returncode;timed_out=False
        rows=load(raw,[]);complete=code==0;coverage=load(str(raw)+'.report.json',{}).get('coverage',{})
    cfg=load(ROOT/'config/sources.json');inbox=load(work/'inbox.json',[])
    index=load(ROOT/'docs/data/archive-index.json',{'issues':[]})
    added,decisions=candidates(rows,inbox,index,cfg)
    report={'since':since,'until':until,'routes':routes,'journals':journals,'collection_exit_code':code,
            'complete':complete,'budget_exhausted':timed_out,'incremental':incremental,
            'applied':False,'additional':len(added),'decisions':decisions,'coverage':coverage}
    # Every snapshot contains complete pages. An interrupted later page cannot
    # invalidate those exact DOI candidates, so incremental runs can publish progress.
    if apply and (complete or incremental):
        if not (work/'auto-state.json').exists():raise RuntimeError('Restore durable state before applying')
        today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
        for row in added:row['collected_date']=today
        write(work/'inbox.json',dedupe_records(inbox+added));report['applied']=True
    write(out/'backfill-report.json',report)
    print('Backfill:',len(added),'additional; complete:',complete,'applied:',report['applied'],flush=True)
    return report


def json_bytes(value):
    import json
    return json.dumps(value,sort_keys=True,ensure_ascii=False).encode()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--since');p.add_argument('--until');p.add_argument('--request',help='Versioned JSON run request, also supported by Actions push trigger')
    p.add_argument('--routes',default='europepmc,biorxiv');p.add_argument('--journals')
    p.add_argument('--work-dir',default='work/cloud');p.add_argument('--output-dir',default='work/backfill')
    p.add_argument('--apply',action='store_true');p.add_argument('--incremental',action='store_true');p.add_argument('--budget-seconds',type=float,default=600);a=p.parse_args()
    if a.request:
        request=load(a.request,{})
        for key in ('since','until','routes','journals'):
            if key in request:setattr(a,key,request[key])
        if not isinstance(request.get('apply',False),bool):p.error('request.apply must be boolean')
        a.apply=request.get('apply',False)
    if not a.since or not a.until:p.error('--since and --until, or --request, are required')
    report=run_backfill(a.since,a.until,a.routes,a.journals,Path(a.work_dir),Path(a.output_dir),
                        a.apply,a.incremental,a.budget_seconds,load(a.request,{}).get('id') if a.request else None)
    if not a.incremental and report['collection_exit_code']:raise SystemExit(report['collection_exit_code'])

if __name__=='__main__':main()
