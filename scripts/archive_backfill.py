"""Explicit, one-time archive import; preserves existing questions and issue IDs."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from common import ROOT,load,write,paper_keys
from reorganize_publication_dates import read_js,week_key,monday_for,entry_for,JST


def reorganize(backfill,today):
    data_dir=ROOT/'docs/data'
    index=load(data_dir/'archive-index.json')
    front=read_js(data_dir/'papers.js')
    recent=read_js(data_dir/'recent-papers.js')
    cutoff=(today-dt.timedelta(days=21)).isoformat()
    moved={p['id']:p for p in front['papers']+recent if p.get('date') and p['date']<cutoff}
    groups={}
    for paper in list(moved.values())+backfill:
        if not paper.get('date'):continue
        groups.setdefault(week_key(paper['date']),{})[paper['id']]=paper
    entries={e['id']:e for e in index['issues']}
    now=dt.datetime.now(JST)
    archive_ids=set()
    for issue_id,additions in groups.items():
        path=data_dir/'issues'/f'{issue_id}.json'
        existing=load(path)
        if existing is None:
            with tempfile.TemporaryDirectory() as tmp:
                source=Path(tmp)/'input.json';target=Path(tmp)/'issue.js';write(source,list(additions.values()))
                subprocess.run([sys.executable,str(ROOT/'scripts/build_issue.py'),str(source),'--id',issue_id,'--out',str(target)],check=True)
                existing=read_js(target)
            monday=monday_for(issue_id)
            existing['issue'].update(date=monday.isoformat(),publication_mode='daily',updated_at=now.isoformat(),week_ends_at=dt.datetime.combine(monday+dt.timedelta(days=7),dt.time(),JST).isoformat())
        known={key for p in existing['papers'] for key in paper_keys(p)}
        # Use the builder for new question options, preserving prior questions verbatim.
        missing=[p for p in additions.values() if not paper_keys(p)&known]
        if missing:
            with tempfile.TemporaryDirectory() as tmp:
                source=Path(tmp)/'input.json';target=Path(tmp)/'issue.js';write(source,missing)
                subprocess.run([sys.executable,str(ROOT/'scripts/build_issue.py'),str(source),'--id',issue_id,'--out',str(target)],check=True)
                existing['papers'].extend(read_js(target)['papers'])
        write(path,existing)
        entries[issue_id]=entry_for(issue_id,existing,path,now)
        archive_ids.update(p['id'] for p in additions.values())
    front['papers']=[p for p in front['papers'] if p['id'] not in moved]
    front_path=data_dir/'issues'/f"{front['issue']['id']}.json"
    # The current issue contains only current papers; retain all its frozen options.
    write(front_path,front)
    entries[front['issue']['id']]=entry_for(front['issue']['id'],front,front_path,now)
    (data_dir/'papers.js').write_text('window.PAPER_DATA = '+json.dumps(front,ensure_ascii=False,indent=2)+';\n')
    recent=[p for p in recent if p['id'] not in archive_ids]
    (data_dir/'recent-papers.js').write_text('window.PAPER_RECENT_DATA = '+json.dumps(recent,ensure_ascii=False,indent=2)+';\n')
    write(data_dir/'archive-index.json',{**index,'issues':sorted(entries.values(),key=lambda e:e['date'])})
    return {'moved_from_current':len(moved),'backfill_archived':len(backfill),'archive_ids':sorted(archive_ids)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--today',required=True);args=p.parse_args()
    rows=[r for r in load(args.input,[]) if all(r.get(k) for k in ('title','abstract','title_ja','abstract_ja','doi'))]
    result=reorganize(rows,dt.date.fromisoformat(args.today));write(ROOT/'work/sar11-archive-report.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
