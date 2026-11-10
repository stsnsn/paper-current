import contextlib,io,json,runpy,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import common
from common import write,load

PROJECT=Path(__file__).resolve().parents[1]

class CollectionResumeTests(unittest.TestCase):
    def collect(self,root,args,fetch):
        with patch.object(common,'ROOT',root),patch.object(sys,'argv',['collect',*args]),patch('requests.get',side_effect=fetch),patch('time.sleep'),contextlib.redirect_stdout(io.StringIO()):
            try:runpy.run_path(str(PROJECT/'scripts/collect.py'),run_name='__main__')
            except SystemExit as exc:return exc.code
        return 0

    def test_europepmc_restarts_at_last_committed_page(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=root/'candidates.json';progress=root/'progress.json'
            cfg={'feeds':[],'source_journals':{'mBio':{'filter':'none'}},'lookback_days':21,'biorxiv_enabled':False}
            write(root/'config/sources.json',cfg)
            args=['--since','2026-11-08','--until','2026-11-10','--routes','europepmc','--journals','mBio','--out',str(raw),'--progress-file',str(progress)]
            calls=[]
            def fetch(url,params=None,**kwargs):
                cursor=params['cursorMark'];calls.append(cursor)
                if cursor=='next':raise requests.ConnectionError('temporary outage')
                return response({'hitCount':2,'nextCursorMark':'next','resultList':{'result':[article(1)]}})
            self.assertEqual(self.collect(root,args,fetch),2)
            self.assertEqual(load(progress)['sources']['Europe PMC journals 1']['cursor'],'next')
            self.assertEqual(len(load(progress)['records']),1)
            calls=[]
            def finish(url,params=None,**kwargs):
                calls.append(params['cursorMark'])
                return response({'hitCount':2,'resultList':{'result':[article(2)]}})
            self.assertEqual(self.collect(root,args,finish),0)
            self.assertEqual(calls,['next'])
            self.assertEqual(len(load(progress)['records']),2)
            self.assertTrue(load(progress)['complete'])
            self.assertEqual(self.collect(root,args,lambda *a,**k:self.fail('Completed query fetched again')),0)

    def test_biorxiv_resumes_offset_and_keeps_previous_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=root/'candidates.json';progress=root/'progress.json'
            write(root/'config/sources.json',{'feeds':[],'lookback_days':21,'europepmc_enabled':False,'biorxiv_enabled':True})
            args=['--since','2026-11-08','--until','2026-11-10','--routes','biorxiv','--out',str(raw),'--progress-file',str(progress)]
            def fetch(url,**kwargs):
                if url.endswith('/1'):raise requests.ConnectionError('temporary outage')
                return response({'messages':[{'total':2}],'collection':[preprint(1)]})
            self.assertEqual(self.collect(root,args,fetch),2)
            self.assertEqual(load(progress)['sources']['bioRxiv']['cursor'],1)
            calls=[]
            def finish(url,**kwargs):
                calls.append(url)
                return response({'messages':[{'total':2}],'collection':[preprint(2)]})
            self.assertEqual(self.collect(root,args,finish),0)
            self.assertEqual(len(calls),1);self.assertTrue(calls[0].endswith('/1'))
            self.assertEqual(len(load(progress)['records']),2)
            self.assertTrue(load(progress)['complete'])


def article(i):
    return {'id':str(i),'source':'MED','doi':f'10.1234/{i}','title':'Microbial genome annotation',
            'abstractText':'Marine bacterial genomes.','firstPublicationDate':'2026-11-09','journalInfo':{'journal':{'title':'mBio'}}}


def preprint(i):
    return {'doi':f'10.1234/{i}','title':'Microbial genome annotation','abstract':'Marine bacterial genomes.',
            'date':'2026-11-09','version':'1'}


def response(data):
    from types import SimpleNamespace
    return SimpleNamespace(raise_for_status=lambda:None,json=lambda:data)
