"""Refresh an unpublished local issue for manual testing. Never pushes to GitHub."""
import argparse,datetime as dt,hashlib,json,subprocess,sys
from pathlib import Path
from common import ROOT,load,write,paper_keys
from auto import eligible,issue_id_for,JST

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work-dir',default=str(ROOT/'work'));args=p.parse_args()
    work=Path(args.work_dir);now=dt.datetime.now(JST);cfg=load(ROOT/'config/automation.json')
    state=load(work/'auto-state.json',{});issue_id=issue_id_for(now)
    if issue_id in state.get('pushed_issues',[]):raise SystemExit('The current issue is confirmed pushed; it cannot be refreshed locally.')
    index=load(ROOT/'docs/data/archive-index.json',{'schema_version':1,'issues':[]})
    used={key for entry in index['issues'] if entry['id']!=issue_id for key in entry.get('doi_keys',[])}
    rows=eligible(load(work/'translated.json',[]),used,now,cfg['max_paper_age_days'])
    if not rows:raise SystemExit('No eligible translated records; existing issue is unchanged.')
    src=work/'local-issue-input.json';draft=work/'local-issue-draft.js';write(src,rows)
    subprocess.run([sys.executable,str(ROOT/'scripts/build_issue.py'),str(src),'--id',issue_id,'--label',issue_id,'--out',str(draft),'--journal-catalog',str(work/'journal-catalog.json')],check=True)
    data=json.loads(draft.read_text().removeprefix('window.PAPER_DATA = ').strip().rstrip(';'));data['issue']['date']=now.date().isoformat()
    payload=ROOT/'docs/data/issues'/f'{issue_id}.json';write(payload,data)
    target=ROOT/'docs/data/papers.js';tmp=target.with_suffix('.tmp');tmp.write_text('window.PAPER_DATA = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n',encoding='utf-8');tmp.replace(target)
    entry={'id':issue_id,'date':now.date().isoformat(),'year':now.year,'month':now.month,'path':'data/issues/'+issue_id+'.json',
        'count':len(data['papers']),'doi_keys':sorted({key for row in data['papers'] for key in paper_keys(row)}),
        'sha256':hashlib.sha256(payload.read_bytes()).hexdigest()}
    index['issues']=[item for item in index['issues'] if item['id']!=issue_id]+[entry]
    write(ROOT/'docs/data/archive-index.json',index)
    print(json.dumps({'issue':issue_id,'journals':sum(not row.get('preprint') for row in rows),'biorxiv':sum(bool(row.get('preprint')) for row in rows)},ensure_ascii=False))
if __name__=='__main__':main()
