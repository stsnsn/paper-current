"""Isolated four-paper / configurable-concurrency CPU benchmark; never writes publication data."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import datetime as dt
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import threading
import time
import requests
from common import load,write
from translate import Translator

MODEL='plamo-3-translate-2b'

def translate_sample(row,base_url,translator_factory=Translator):
    translator=translator_factory(base_url,MODEL,4096)
    result={**row,'fields':{},'success':True}
    started=time.perf_counter()
    for field in ('title','abstract'):
        begin=time.perf_counter()
        try:
            value=translator.translate(row[field])
            result['fields'][field]={'translation':value,'input_chars':len(row[field]),'output_chars':len(value)}
        except Exception as exc:
            result['success']=False
            result['fields'][field]={'error':str(exc),'input_chars':len(row[field])}
        result['fields'][field]['seconds']=round(time.perf_counter()-begin,3)
    result['seconds']=round(time.perf_counter()-started,3)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,choices=(2,4),default=2)
    parser.add_argument('--server',required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--fixture',default='tests/fixtures/plamo-benchmark.json')
    parser.add_argument('--out-dir',required=True)
    args=parser.parse_args()
    rows=load(args.fixture)
    if len(rows)!=4 or len({r['id'] for r in rows})!=4:parser.error('Exactly four unique samples required')
    if any(r.get('rights_status')!='allowed' or not r.get('title') or not r.get('abstract') for r in rows):parser.error('All samples must be publication-eligible with title and abstract')
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    report={'started_at':dt.datetime.now(dt.timezone.utc).isoformat(),'workers':args.workers,'count':4,'context_per_slot':8192,
            'hardware':{'platform':platform.platform(),'cpu_count':os.cpu_count()},
            'model':MODEL,'model_revision':os.getenv('MODEL_REVISION'),'model_sha256':os.getenv('MODEL_SHA256'),
            'llama_revision':os.getenv('LLAMA_REVISION'),'results':[],'status':'starting'}
    write(out/'report.json',report)
    command=[args.server,'-m',args.model,'--alias',MODEL,'--host','127.0.0.1','--port','18080',
             '--parallel',str(args.workers),'--ctx-size',str(8192*args.workers),'--threads',str(os.cpu_count() or 2),
             '--threads-batch',str(os.cpu_count() or 2),'--n-gpu-layers','0']
    stop=threading.Event();peak_rss=[0];session=requests.Session();session.trust_env=False
    with (out/'server.log').open('w') as log:
        started=time.perf_counter();server=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        def sample_memory():
            while not stop.wait(.1):
                try:
                    for line in Path('/proc/'+str(server.pid)+'/status').read_text().splitlines():
                        if line.startswith('VmRSS:'):peak_rss[0]=max(peak_rss[0],int(line.split()[1]))
                except (FileNotFoundError,ProcessLookupError):pass
        sampler=threading.Thread(target=sample_memory,daemon=True);sampler.start()
        try:
            deadline=time.monotonic()+240
            while True:
                if server.poll() is not None:raise RuntimeError('llama-server exited during startup; see server.log')
                try:
                    if session.get('http://127.0.0.1:18080/health',timeout=3).status_code==200:break
                except requests.RequestException:pass
                if time.monotonic()>deadline:raise TimeoutError('Model startup exceeded 240 seconds')
                time.sleep(1)
            Translator('http://127.0.0.1:18080/v1',MODEL).connect()
            report['startup_seconds']=round(time.perf_counter()-started,3);report['status']='translating'
            write(out/'report.json',report)
            begin=time.perf_counter()
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures=[executor.submit(translate_sample,row,'http://127.0.0.1:18080/v1') for row in rows]
                for future in as_completed(futures):
                    result=future.result();report['results'].append(result)
                    write(out/'report.json',report)
                    print(json.dumps({'id':result['id'],'seconds':result['seconds'],'success':result['success']}),flush=True)
            report['translation_seconds']=round(time.perf_counter()-begin,3)
            report['status']='complete' if all(r['success'] for r in report['results']) else 'failed'
        except Exception as exc:
            report['status']='failed';report['error']=str(exc)
        finally:
            server.terminate()
            try:server.wait(timeout=15)
            except subprocess.TimeoutExpired:server.kill();server.wait()
            stop.set();sampler.join(timeout=2)
            report['server_peak_rss_kib']=max(peak_rss[0],resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
            report['total_seconds']=round(time.perf_counter()-started,3)
            write(out/'report.json',report)
    lines=['# PLaMo CPU benchmark','',f"Status: {report['status']}",'',
           f'4 papers, {args.workers} concurrent requests; each paper: title, then abstract.',
           '',f"Translation wall time: {report.get('translation_seconds','n/a')} seconds",
           f"Model startup: {report.get('startup_seconds','n/a')} seconds",
           f"Server peak RSS: {report['server_peak_rss_kib']/1024:.1f} MiB",'',
           '| DOI | Title (s) | Abstract (s) | Paper (s) | Success |','|---|---:|---:|---:|---|']
    for r in report['results']:
        lines.append(f"| {r.get('doi',r['id'])} | {r['fields']['title']['seconds']} | {r['fields']['abstract']['seconds']} | {r['seconds']} | {r['success']} |")
    (out/'summary.md').write_text('\n'.join(lines)+'\n')
    return 0 if report['status']=='complete' else 1

if __name__=='__main__':raise SystemExit(main())
