"""Bounded GitHub Actions pipeline. License metadata does not restrict processing."""
import argparse
from contextlib import contextmanager
import datetime as dt
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import requests
import auto
from common import ROOT,load,write,dedupe_records,paper_keys
from topic_filter import annotate
from journal_catalog import update_catalog
from translate import Translator,translate_records
from translate_queue import is_complete,ordered_groups
from collection_window import advance_sources
from rss_records import normalize_rss_record
from normalize_rss_data import repair_record

FILES=('inbox.json','translated.json','translation-retries.json','auto-state.json','journal-catalog.json','cloud-status.json')
LOG=logging.getLogger('cloud-daily')

def git(path,*args):
    return subprocess.check_output(['git','-C',str(path),*args],text=True).strip()

def allowed_rows(rows,now,retention=90):
    cutoff=now.astimezone(auto.JST).date()-dt.timedelta(days=retention)
    result=[]
    for row in dedupe_records(rows):
        for field in ('collected_date','date'):
            try:arrival=dt.date.fromisoformat(str(row.get(field) or '')[:10])
            except ValueError:continue
            if arrival>=cutoff:result.append(row)
            break
    return result

def sanitize(work,now):
    rows=allowed_rows([normalize_rss_record(r) for r in load(work/'inbox.json',[])],now)
    ids={r['id'] for r in rows}
    write(work/'inbox.json',rows)
    write(work/'translated.json',[repair_record(r) for r in dedupe_records(load(work/'translated.json',[])) if r['id'] in ids])
    write(work/'translation-retries.json',{k:v for k,v in load(work/'translation-retries.json',{}).items() if k in ids})

def restore_state(work,state_dir):
    source=state_dir/'state';manifest=load(source/'manifest.json')
    if not manifest or manifest.get('schema_version')!=1:raise RuntimeError('Durable automation state missing; refusing an empty restart')
    for name in FILES:
        path=source/name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['sha256'].get(name):raise RuntimeError('State hash mismatch: '+name)
    work.mkdir(parents=True,exist_ok=True)
    for name in FILES:shutil.copyfile(source/name,work/name)

def save_state(work,state_dir,now=None):
    now=now or dt.datetime.now(dt.timezone.utc);sanitize(work,now)
    dest=state_dir/'state';dest.mkdir(parents=True,exist_ok=True)
    for name in FILES:
        if not (work/name).exists():write(work/name,{} if name not in ('inbox.json','translated.json','journal-catalog.json') else [])
        shutil.copyfile(work/name,dest/name)
    write(dest/'manifest.json',{'schema_version':1,'saved_at':now.isoformat(),
          'sha256':{name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in FILES}})
    git(state_dir,'config','user.name','github-actions[bot]')
    git(state_dir,'config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    git(state_dir,'add','state')
    if git(state_dir,'diff','--cached','--name-only'):
        git(state_dir,'commit','-m','Checkpoint Paper Current automation')
        git(state_dir,'push','origin','HEAD:refs/heads/automation-state')

def process_backfill_request(work):
    request_path=ROOT/'config/backfill-request.json'
    request=load(request_path,{})
    if not request:return False
    identifier=request.get('id')
    if not isinstance(identifier,str) or not identifier:raise ValueError('Backfill request needs a stable id')
    state=load(work/'auto-state.json',{})
    if identifier in state.get('completed_backfill_requests',[]):return False
    subprocess.run([sys.executable,str(ROOT/'scripts/backfill.py'),'--request',str(request_path),
                    '--work-dir',str(work),'--output-dir',str(work.parent/'backfill')],check=True,timeout=3600)
    report=load(work.parent/'backfill/backfill-report.json',{})
    if report.get('collection_exit_code')!=0 or (request.get('apply') and not report.get('applied')):
        raise RuntimeError('Backfill request did not complete')
    state.setdefault('completed_backfill_requests',[]).append(identifier)
    write(work/'auto-state.json',state)
    return True

def pending_rows(work,now,model):
    sources=load(ROOT/'config/sources.json');cfg=load(ROOT/'config/automation.json')
    used={k for i in auto.archive_index()['issues'] for k in i.get('doi_keys',[])}
    old={r['id']:r for r in load(work/'translated.json',[])}
    candidates=[];retries=load(work/'translation-retries.json',{})
    for row in load(work/'inbox.json',[]):
        r=annotate(row,sources)
        if (not r.get('title') or not r.get('abstract') or not r.get('doi')
            or not r['topic_filter']['accepted']):continue
        try:age=(now.astimezone(auto.JST).date()-dt.date.fromisoformat(r.get('collected_date') or r.get('date','')[:10])).days
        except ValueError:continue
        if not 0<=age<=cfg['max_paper_age_days'] or is_complete(r,old,model):continue
        # Repair an invalidated existing cache even for issued papers. The issue
        # builder still prevents duplicates; recent reading data needs a valid copy.
        if paper_keys(r)&used and r['id'] not in old:continue
        retry=retries.get(r['id'],{})
        input_hash=hashlib.sha256((r['title']+'\n'+r.get('abstract','')+'|'+model).encode()).hexdigest()
        if retry.get('input_hash')==input_hash and retry.get('next_retry','')>now.isoformat():continue
        candidates.append(r)
    return ordered_groups([r for r in candidates if not r.get('preprint')])+ordered_groups([r for r in candidates if r.get('preprint')])

def collection_due(last,now,cfg):
    if not last:return True
    previous=dt.datetime.fromisoformat(last)
    elapsed=(now-previous).total_seconds()
    if elapsed>=cfg['collect_interval_hours']*3600:return True
    if cfg['collect_interval_hours']==24:
        # Schedule jitter must not skip tomorrow's 09:17 run or drift to a recovery slot.
        local=now.astimezone(auto.JST);old=previous.astimezone(auto.JST)
        boundary=dt.timedelta(hours=cfg['publish_hour_jst'])
        return local.hour>=cfg['publish_hour_jst'] and (local-boundary).date()>(old-boundary).date()
    return False

def prepare(work,now,cloud):
    cfg=load(ROOT/'config/automation.json');state=load(work/'auto-state.json',{})
    last=state.get('last_local_collect');collected=False
    if collection_due(last,now,cfg):
        state.setdefault('source_collection_baseline',last or (now-dt.timedelta(days=load(ROOT/'config/sources.json')['lookback_days'])).isoformat())
        write(work/'auto-state.json',state)
        old_ids={row.get('id') for row in load(work/'inbox.json',[]) if row.get('id')}
        report_path=Path(str(work/'inbox.json')+'.report.json')
        report_path.unlink(missing_ok=True)
        try:
            result=subprocess.run([sys.executable,str(ROOT/'scripts/collect.py'),'--out',str(work/'inbox.json'),'--source-state',str(work/'auto-state.json')],timeout=cloud['collection_timeout_seconds'])
            state['last_collection_attempt']=now.isoformat();state['collection_exit_code']=result.returncode
            # This cursor schedules daily attempts; each source has its own
            # successful cursor for the next request's date range.
            report=load(report_path,{})
            if result.returncode==0 or (result.returncode==2 and any(v.get('ok') for v in report.get('coverage',{}).values())):
                state['last_local_collect']=now.isoformat()
            collected=True
        except subprocess.TimeoutExpired:
            state['last_collection_attempt']=now.isoformat();state['collection_exit_code']='timeout'
            LOG.warning('Collection timed out; saved candidates remain available')
        advance_sources(state,load(report_path,{}).get('coverage',{}),now)
        # New records belong to the week they entered the system, even when a
        # feed or bibliographic index reports an older publication date.
        inbox=load(work/'inbox.json',[]);collection_day=now.astimezone(auto.JST).date().isoformat()
        changed=False
        for row in inbox:
            if row.get('id') not in old_ids and not row.get('collected_date'):
                row['collected_date']=collection_day;changed=True
        if changed:write(work/'inbox.json',inbox)
    write(work/'auto-state.json',state);sanitize(work,now)
    write(work/'journal-catalog.json',update_catalog(load(work/'journal-catalog.json',[]),load(work/'inbox.json',[]),load(ROOT/'config/sources.json').get('feed_journals',{})))
    queue=pending_rows(work,now,cloud['model'])
    write(work/'cloud-status.json',{'updated_at':now.isoformat(),'phase':'prepared','pending':len(queue),'collection_attempted':collected,'collection_exit_code':state.get('collection_exit_code')})
    output=os.getenv('GITHUB_OUTPUT')
    if output:
        with open(output,'a') as f:f.write('needs_translation='+str(bool(queue)).lower()+'\n')
    return len(queue)

@contextmanager
def model_server(binary,model_file,workers,model,work):
    log=(work/'model-server.log').open('w')
    cpu=str(len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count() or 2)
    server=subprocess.Popen([binary,'-m',model_file,'--alias',model,'--host','127.0.0.1','--port','18080',
        '--parallel',str(workers),'--ctx-size',str(8192*workers),'--threads',cpu,'--threads-batch',cpu,'--n-gpu-layers','0'],stdout=log,stderr=subprocess.STDOUT)
    session=requests.Session();session.trust_env=False
    try:
        deadline=time.monotonic()+240
        while True:
            if server.poll() is not None:raise RuntimeError('Model server exited; see model-server.log')
            try:
                if session.get('http://127.0.0.1:18080/health',timeout=3).status_code==200:break
            except requests.RequestException:pass
            if time.monotonic()>deadline:raise TimeoutError('Model startup exceeded 240 seconds')
            time.sleep(1)
        yield Translator('http://127.0.0.1:18080/v1',model).connect()
    finally:
        server.terminate()
        try:server.wait(timeout=15)
        except subprocess.TimeoutExpired:server.kill();server.wait()
        log.close()

def translate(work,state_dir,cloud,binary,model_file):
    deadline=time.monotonic()+cloud['translation_minutes']*60
    with model_server(binary,model_file,cloud['workers'],cloud['model'],work) as translator:
        while time.monotonic()<deadline:
            now=dt.datetime.now(dt.timezone.utc);rows=pending_rows(work,now,cloud['model'])[:cloud['batch_size']]
            if not rows:break
            stats=translate_records(rows,work/'translated.json',translator,workers=cloud['workers'],keep_going=True,retry_state=work/'translation-retries.json')
            write(work/'cloud-status.json',{'updated_at':now.isoformat(),'phase':'translating','last_batch':stats,'pending':len(pending_rows(work,dt.datetime.now(dt.timezone.utc),cloud['model']))})
            save_state(work,state_dir)
    status=load(work/'cloud-status.json',{});status.update(phase='translated',updated_at=dt.datetime.now(dt.timezone.utc).isoformat());write(work/'cloud-status.json',status)

def publish(work,now,model):
    previous={r['id']:r for r in load(work/'translated.json',[])};sources=load(ROOT/'config/sources.json')
    ready=[]
    for source in load(work/'inbox.json',[]):
        row=annotate(source,sources)
        if (row.get('title') and row.get('abstract') and row.get('doi')
            and row['topic_filter']['accepted']
            and is_complete(row,previous,model)):
            record={**previous[row['id']],**row}
            # Current translations come from the validated cache, never inbox copies.
            for field in ('title_ja','abstract_ja','translation','translation_label'):
                if field in previous[row['id']]:record[field]=previous[row['id']][field]
            ready.append(record)
    local=now.astimezone(auto.JST).date();cutoff=local-dt.timedelta(days=6)
    recent=[]
    for row in ready:
        try:arrival=dt.date.fromisoformat(row.get('collected_date') or row.get('date','')[:10])
        except ValueError:continue
        if arrival>=cutoff:
            if not row.get('archive_only'):recent.append(row)
    recent.sort(key=lambda row:(str(row.get('collected_at') or row.get('collected_date') or row.get('first_seen','')),str(row.get('id',''))))
    recent_path=ROOT/'docs/data/recent-papers.js'
    recent_path.parent.mkdir(parents=True,exist_ok=True)
    recent_path.write_text('window.PAPER_RECENT_DATA = '+json.dumps(recent,ensure_ascii=False,indent=2)+';\n',encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='cloud-issue-') as tmp:
        staging=Path(tmp);write(staging/'translated.json',ready);shutil.copyfile(work/'journal-catalog.json',staging/'journal-catalog.json')
        state=load(work/'auto-state.json',{});result=auto.build_daily(load(ROOT/'config/automation.json'),staging,state,now)
        write(work/'auto-state.json',state)
    status=load(work/'cloud-status.json',{});status.update(phase='built',updated_at=now.isoformat(),publication=result);write(work/'cloud-status.json',status)
    from build_explorer import build as build_explorer
    build_explorer(ROOT)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['restore','prepare','translate','publish','confirm','save','backfill-request'])
    p.add_argument('--work-dir',default='work/cloud');p.add_argument('--state-dir',default='.automation-state');p.add_argument('--server');p.add_argument('--model-file');a=p.parse_args()
    logging.basicConfig(level=logging.INFO)
    work=Path(a.work_dir).resolve();state_dir=Path(a.state_dir).resolve();cloud=load(ROOT/'config/cloud.json');now=dt.datetime.now(dt.timezone.utc)
    if a.phase=='restore':restore_state(work,state_dir)
    elif a.phase=='backfill-request':process_backfill_request(work)
    elif a.phase=='prepare':prepare(work,now,cloud)
    elif a.phase=='translate':translate(work,state_dir,cloud,a.server,a.model_file)
    elif a.phase=='publish':print('Publication:',publish(work,now,cloud['model']))
    elif a.phase=='confirm':
        state=load(work/'auto-state.json',{});index=auto.archive_index()
        state['pushed_issues']=sorted(set(state.get('pushed_issues',[]))|{i['id'] for i in index['issues']})
        state['pushed_hashes']={**state.get('pushed_hashes',{}),**{i['id']:i['sha256'] for i in index['issues']}}
        state['last_cloud_publication_check']=now.isoformat();write(work/'auto-state.json',state)
    elif a.phase=='save':save_state(work,state_dir,now)

if __name__=='__main__':main()
