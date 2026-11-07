import http.server,json,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PipelineTests(unittest.TestCase):
 def test_translation_cache_and_truncation(self):
  calls=[];truncated=[False]
  class Handler(http.server.BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):
    self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'data':[{'id':'plamo-test'}]}).encode())
   def do_POST(self):
    data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append(data)
    assert '<|plamo:key|>lang<|plamo:val|>ja' in data['prompt'];assert self.path=='/v1/completions'
    self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'choices':[{'text':'翻訳結果','finish_reason':'length' if truncated[0] else 'stop'}]}).encode())
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
  try:
   with tempfile.TemporaryDirectory() as tmp:
    src=Path(tmp)/'in.json';out=Path(tmp)/'out.json';src.write_text(json.dumps([{'id':'x','title':'A title','abstract':'A study','rights_status':'allowed'}]))
    cmd=[sys.executable,str(ROOT/'scripts/translate.py'),str(src),'--output',str(out),'--retry-state',str(Path(tmp)/'retry.json'),'--base-url',f'http://127.0.0.1:{server.server_port}/v1']
    r=subprocess.run(cmd,capture_output=True);self.assertEqual(r.returncode,0,r.stderr.decode());self.assertEqual(len(calls),2)
    r=subprocess.run(cmd,capture_output=True);self.assertEqual(r.returncode,0,r.stderr.decode());self.assertEqual(len(calls),2)
    truncated[0]=True
    self.assertNotEqual(subprocess.run(cmd+['--force'],capture_output=True).returncode,0)
    self.assertEqual(json.loads(out.read_text())[0]['abstract_ja'],'翻訳結果')
  finally:server.shutdown();server.server_close()
 def test_build_eligibility_unique_options(self):
  with tempfile.TemporaryDirectory() as tmp:
   rows=json.loads((ROOT/'docs/data/demo.json').read_text());rows[0]['rights_status']='pending';rows[1]['preprint']=True;rows[2]['abstract_ja']='';rows[3]['review']=True
   src=Path(tmp)/'in.json';out=Path(tmp)/'papers.js';src.write_text(json.dumps(rows))
   cmd=[sys.executable,str(ROOT/'scripts/build_issue.py'),str(src),'--id','test','--out',str(out)]
   self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
   first=out.read_bytes();d=json.loads(out.read_text().removeprefix('window.PAPER_DATA = ').strip().rstrip(';'))
   self.assertEqual(len(d['papers']),9);self.assertTrue(all('rights_status' not in p for p in d['papers']));self.assertTrue(any(p.get('review') for p in d['papers']))
   for p in d['papers']:self.assertEqual(len(set(p['options'])),4);self.assertEqual(p['options'].count(p['answer_journal']),1) if p['answer_journal'] else self.assertNotIn('bioRxiv',p['options'])
   subprocess.run(cmd,check=True,capture_output=True);self.assertEqual(first,out.read_bytes())
if __name__=='__main__':unittest.main()
