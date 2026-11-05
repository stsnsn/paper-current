import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import auto
from common import load,write

class ArchiveTests(unittest.TestCase):
    def setup_repo(self,base):
        root=base/'source';root.mkdir();remote=base/'remote.git'
        def run(*args,cwd=root):
            return subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True).stdout
        run('git','init','--bare',str(remote));run('git','init','-b','main')
        run('git','config','user.name','Test');run('git','config','user.email','test@example.invalid')
        run('git','remote','add','origin',str(remote))
        (root/'docs/data').mkdir(parents=True)
        write(root/'docs/data/archive-index.json',{'schema_version':1,'archive_after_days':90,'issues':[]})
        (root/'docs/data/papers.js').write_text('window.PAPER_DATA = {};')
        run('git','add','.');run('git','commit','-m','Initial');run('git','push','-u','origin','main')
        return root,remote
    def make_issue(self,root):
        payload={'issue':{'id':'2026-W01','date':'2026-01-01'},'papers':[{'id':'10.1234/old','doi':'10.1234/old'}]}
        path=root/'docs/data/issues/2026-W01.json';write(path,payload)
        entry={'id':'2026-W01','date':'2026-01-01','year':2026,'month':1,'path':'data/issues/2026-W01.json','count':1,'doi_keys':['10.1234/old'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        write(root/'docs/data/archive-index.json',{'schema_version':1,'archive_after_days':90,'issues':[entry]})
        (root/'docs/data/papers.js').write_text('window.PAPER_DATA = '+json.dumps(payload)+';')
        return path,entry
    def test_push_archives_remotely_and_evicts_local_after_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,remote=self.setup_repo(Path(tmp));path,entry=self.make_issue(root)
            blob=subprocess.run(['git','hash-object',str(path)],capture_output=True,text=True,check=True).stdout.strip()
            work=root/'work';write(work/'inbox.json',[{'id':'10.1234/old','doi':'10.1234/old'},{'id':'10.1234/new','doi':'10.1234/new'}]);write(work/'translated.json',load(work/'inbox.json'))
            state={};cfg=load(ROOT/'config/automation.json');now=dt.datetime(2026,11,6,tzinfo=dt.timezone.utc)
            with patch.object(auto,'ROOT',root):auto.push_pending(cfg,work,state,now)
            self.assertFalse(path.exists());self.assertEqual(load(work/'inbox.json')[0]['doi'],'10.1234/new')
            self.assertEqual(state['pushed_issues'],['2026-W01'])
            remote_data=subprocess.run(['git','--git-dir',str(remote),'show','main:docs/data/issues/2026-W01.json'],capture_output=True,text=True,check=True).stdout
            self.assertEqual(json.loads(remote_data)['issue']['id'],'2026-W01')
            # The publishing clone was temporary: source Git has no archive blob.
            self.assertNotEqual(subprocess.run(['git','cat-file','-e',blob],cwd=root,capture_output=True).returncode,0)
            self.assertIn('10.1234/old',load(root/'docs/data/archive-index.json')['issues'][0]['doi_keys'])
    def test_failed_push_does_not_delete_generated_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,remote=self.setup_repo(Path(tmp));path,entry=self.make_issue(root)
            work=root/'work';work.mkdir();state={};cfg=load(ROOT/'config/automation.json');cfg['remote_url']=str(Path(tmp)/'nonexistent.git')
            with patch.object(auto,'ROOT',root),self.assertRaises(RuntimeError):auto.push_pending(cfg,work,state,dt.datetime.now(dt.timezone.utc))
            self.assertTrue(path.exists());self.assertNotIn('pushed_issues',state)

if __name__=='__main__':unittest.main()
