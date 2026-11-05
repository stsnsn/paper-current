"""Local RSS collection, PLaMo translation and weekly git push.
GitHub Actions deploys static files only. Archive payloads are evicted locally
only after a successful push; a small DOI/month index remains.
"""
import argparse
from contextlib import contextmanager
import datetime as dt
import json
import hashlib
import shutil
import tempfile
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys
import time
from common import ROOT,load,write,dedupe_records,paper_keys
from translate import Translator,translate_records
JST=dt.timezone(dt.timedelta(hours=9))
LOG=logging.getLogger('paper-current')

def command(argv,*,cwd=None,input_text=None):
    r=subprocess.run(argv,cwd=cwd or ROOT,text=True,capture_output=True,encoding='utf-8',input=input_text)
    if r.returncode:raise RuntimeError(f'{argv[0]} failed: '+r.stderr.strip()[:1500])
    return r.stdout

@contextmanager
def worker_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True);handle=path.open('a+b')
    try:
        if os.name=='nt':
            import msvcrt
            handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        handle.close();raise RuntimeError('Another auto.py worker is already running')
    try:yield
    finally:
        if os.name=='nt':handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        handle.close()

def merge_inbox(path,rows):
    merged=dedupe_records(load(path,[])+rows);write(path,merged);return len(merged)

def collect_local(cfg,work,state,now):
    last=state.get('last_local_collect')
    if last and now-dt.datetime.fromisoformat(last)<dt.timedelta(hours=cfg['collect_interval_hours']):return False
    r=subprocess.run([sys.executable,str(ROOT/'scripts/collect.py'),'--out',str(work/'inbox.json')],cwd=ROOT)
    if r.returncode==0:state['last_local_collect']=now.isoformat();write(work/'auto-state.json',state)
    else:LOG.warning('Collection incomplete; retrying next cycle')
    return (work/'inbox.json').exists()

def eligible(rows,used,now,max_age_days):
    out=[]
    for a in dedupe_records(rows):
        if paper_keys(a)&used or a.get('rights_status')!='allowed' or a.get('review'):continue
        if not all(a.get(k) for k in ('title','abstract','title_ja','abstract_ja','doi')):continue
        if not a.get('journal') and not a.get('preprint'):continue
        try:date=dt.date.fromisoformat(a.get('date','')[:10])
        except ValueError:continue
        if 0<=(now.date()-date).days<=max_age_days:out.append(a)
    return out

def archive_index():
    return load(ROOT/'docs/data/archive-index.json',{'schema_version':1,'archive_after_days':90,'issues':[]})

def issue_id_for(now):
    iso=now.astimezone(JST).isocalendar();return f'{iso.year}-W{iso.week:02d}'

def build_week(cfg,work,state,now):
    local=now.astimezone(JST);monday=local.date()-dt.timedelta(days=local.weekday())
    due=dt.datetime.combine(monday+dt.timedelta(days=cfg['publish_weekday']),dt.time(cfg['publish_hour_jst']),tzinfo=JST)
    if local<due:return 'not_due'
    issue_id=issue_id_for(now);index=archive_index()
    # The lightweight index is sufficient when archive bodies are absent locally.
    if any(i['id']==issue_id for i in index['issues']):return 'already_built'
    used={key for i in index['issues'] for key in i.get('doi_keys',[])}
    rows=eligible(load(work/'translated.json',[]),used,local,cfg['max_paper_age_days'])
    if len(rows)<cfg['minimum_questions']:
        LOG.info('Weekly issue waiting: %d eligible / minimum %d',len(rows),cfg['minimum_questions']);return 'waiting'
    src=work/'issue-input.json';draft=work/'issue-draft.js';write(src,rows)
    iso=local.isocalendar()
    command([sys.executable,str(ROOT/'scripts/build_issue.py'),str(src),'--id',issue_id,'--label',f'{iso.year} W{iso.week:02d}','--out',str(draft)])
    data=json.loads(draft.read_text().removeprefix('window.PAPER_DATA = ').strip().rstrip(';'))
    data['issue']['date']=local.date().isoformat()
    payload_path=ROOT/'docs/data/issues'/f'{issue_id}.json';write(payload_path,data)
    # Preserve the previous front page until the archive payload is durable.
    target=ROOT/'docs/data/papers.js';tmp=target.with_suffix('.tmp')
    tmp.write_text('window.PAPER_DATA = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n');tmp.replace(target)
    entry={'id':issue_id,'date':local.date().isoformat(),'year':local.year,'month':local.month,
        'path':'data/issues/'+issue_id+'.json','count':len(data['papers']),
        'doi_keys':sorted({key for a in data['papers'] for key in paper_keys(a)}),
        'sha256':hashlib.sha256(payload_path.read_bytes()).hexdigest()}
    index['archive_after_days']=cfg['archive_after_days'];index['issues'].append(entry)
    write(ROOT/'docs/data/archive-index.json',index)
    state['last_built_issue']=issue_id;write(work/'auto-state.json',state)
    LOG.info('Built %s: %d papers',issue_id,len(rows));return 'built'

# Backward-compatible import used by tests and local integrations.
def publish_week(cfg,work,state,now,push=False):
    status=build_week(cfg,work,state,now)
    if push or cfg.get('auto_push'):
        if status in ('built','already_built'):push_pending(cfg,work,state,now)
    return status

def push_pending(cfg,work,state,now):
    index=archive_index();confirmed=set(state.get('pushed_issues',[]))
    pending=[i for i in index['issues'] if i['id'] not in confirmed and (ROOT/'docs'/i['path']).exists()]
    if not pending:return
    branch=cfg.get('branch','main')
    remote=cfg.get('remote_url') or command(['git','remote','get-url','origin']).strip()
    if '://' in remote and '@' in remote.split('://',1)[1].split('/',1)[0]:
        raise RuntimeError('Use Git credential storage instead of embedding credentials in remote_url')
    # Only the latest issue and DOI index are checked out. Archive blobs remain
    # on GitHub. Even newly created Git objects live only in this temporary repo.
    with tempfile.TemporaryDirectory(prefix='paper-current-publish-') as tmp:
        checkout=Path(tmp)/'repo'
        command(['git','clone','--filter=blob:none','--depth=1','--no-checkout','--single-branch','--branch',branch,remote,str(checkout)])
        command(['git','sparse-checkout','init','--no-cone'],cwd=checkout)
        command(['git','sparse-checkout','set','--no-cone','--stdin'],cwd=checkout,
            input_text='/docs/data/archive-index.json\n/docs/data/papers.js\n')
        command(['git','checkout',branch],cwd=checkout)
        remote_index=load(checkout/'docs/data/archive-index.json',{'schema_version':1,'issues':[]})
        remote_by_id={i['id']:i for i in remote_index['issues']}
        for i in pending:
            previous=remote_by_id.get(i['id'])
            if previous and (previous.get('sha256')!=i.get('sha256') or previous.get('doi_keys')!=i.get('doi_keys')):
                raise RuntimeError('Remote issue already exists with different content: '+i['id'])
            remote_by_id[i['id']]=i
            target=checkout/'docs'/i['path'];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/'docs'/i['path'],target)
        merged_index={**remote_index,'schema_version':1,'archive_after_days':cfg['archive_after_days'],
            'issues':sorted(remote_by_id.values(),key=lambda i:i['date'])}
        write(checkout/'docs/data/archive-index.json',merged_index)
        newest=max(merged_index['issues'],key=lambda i:i['date'])
        if newest['id'] in {i['id'] for i in pending}:
            shutil.copyfile(ROOT/'docs/data/papers.js',checkout/'docs/data/papers.js')
        allowed=['docs/data/papers.js','docs/data/archive-index.json']+['docs/'+i['path'] for i in pending]
        command(['git','add','--sparse','--',*allowed],cwd=checkout)
        if command(['git','diff','--cached','--name-only'],cwd=checkout).strip():
            # Inherit the user's existing Git identity, including repo-local config.
            name=command(['git','config','user.name']).strip()
            email=command(['git','config','user.email']).strip()
            command(['git','-c','user.name='+name,'-c','user.email='+email,'commit','-m','Publish Paper Current '+pending[-1]['id']],cwd=checkout)
        command(['git','push','origin',branch],cwd=checkout)
    write(ROOT/'docs/data/archive-index.json',merged_index)

    # No deletion or local eviction happens before push succeeds.
    confirmed.update(i['id'] for i in pending);state['pushed_issues']=sorted(confirmed)
    write(work/'auto-state.json',state)
    cleanup_local(cfg,work,state,now)
    LOG.info('Pushed %d weekly issue(s)',len(pending))

def cleanup_local(cfg,work,state,now):
    index=archive_index();confirmed=set(state.get('pushed_issues',[]))
    cutoff=now.astimezone(JST).date()-dt.timedelta(days=cfg['local_retention_days'])
    old=[i for i in index['issues'] if i['id'] in confirmed and dt.date.fromisoformat(i['date'])<=cutoff]
    keys={k for i in old for k in i.get('doi_keys',[])}
    # Prune application queues only for old, confirmed-pushed papers.
    for name in ('inbox.json','translated.json'):
        path=work/name
        if path.exists():write(path,[a for a in load(path,[]) if not paper_keys(a)&keys])
    retries=load(work/'translation-retries.json',{})
    if retries:write(work/'translation-retries.json',{k:v for k,v in retries.items() if k not in keys})
    for name in ('issue-input.json','issue-draft.js'):
        (work/name).unlink(missing_ok=True)
    # These are generated data files, not edits to source or a Git index.
    # Git objects were created in the temporary checkout, which is now gone.
    for i in index['issues']:
        if i['id'] in confirmed:(ROOT/'docs'/i['path']).unlink(missing_ok=True)



def cycle(cfg,work,state,now=None,push=False):
    now=now or dt.datetime.now(dt.timezone.utc)
    try:collect_local(cfg,work,state,now)
    except Exception:LOG.exception('Collection unavailable; processing saved queue')
    index=archive_index();used={k for i in index['issues'] for k in i.get('doi_keys',[])}
    rows=load(work/'inbox.json',[])
    # Keep aliases in the index but avoid re-translating already issued papers.
    pending=[a for a in rows if not paper_keys(a)&used]
    if pending:
        try:
            translator=Translator(cfg['base_url'],cfg.get('model'),cfg['max_tokens']).connect()
            LOG.info('Translations: %s',translate_records(pending,work/'translated.json',translator,
                limit=cfg['max_papers_per_cycle'],keep_going=True,retry_state=work/'translation-retries.json',now=now))
        except Exception:LOG.exception('LM Studio unavailable; saved queue will resume')
    try:publish_week(cfg,work,state,now,push)
    except Exception:LOG.exception('Weekly publication failed; will retry')
    try:cleanup_local(cfg,work,state,now)
    except Exception:LOG.exception('Local archive cleanup deferred')
    write(work/'status.json',{'updated_at':now.isoformat(),'collected':len(load(work/'inbox.json',[])),
        'translated':sum(bool(a.get('title_ja') and a.get('abstract_ja')) for a in load(work/'translated.json',[])),
        'retrying':len(load(work/'translation-retries.json',{})),'last_built_issue':state.get('last_built_issue'),
        'note':'See auto.log for errors and source coverage.'})

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',default=str(ROOT/'config/automation.json'));p.add_argument('--once',action='store_true')
    p.add_argument('--publish',action='store_true',help='Commit/push weekly static data to origin')
    p.add_argument('--work-dir',default=str(ROOT/'work'));args=p.parse_args()
    cfg=load(args.config)
    if cfg['poll_seconds']<30:p.error('poll_seconds must be at least 30')
    if not 0<=cfg['publish_weekday']<=6 or not 0<=cfg['publish_hour_jst']<=23:p.error('Invalid weekly schedule')
    work=Path(args.work_dir).resolve();work.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',handlers=[logging.StreamHandler(),RotatingFileHandler(work/'auto.log',maxBytes=2_000_000,backupCount=3,encoding='utf-8')])
    with worker_lock(work/'auto.lock'):
        state=load(work/'auto-state.json',{})
        while True:
            cycle(cfg,work,state,push=args.publish)
            if args.once:break
            time.sleep(cfg['poll_seconds'])

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('Stopped. Queue saved.')
