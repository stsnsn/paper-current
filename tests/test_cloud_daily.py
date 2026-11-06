import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import cloud_daily as cloud
import auto
from common import write,load
from translate import fingerprint

NOW=dt.datetime(2026,11,7,3,tzinfo=dt.timezone.utc)
def row(i,rights='allowed'):
    return {'id':'10.1234/'+str(i),'doi':'10.1234/'+str(i),'date':'2026-11-06','journal':'mBio','title':'Microbial genomes '+str(i),'abstract':'Marine microbial ecology','rights_status':rights}
def translated(r,model='test'):
    return {**r,'title_ja':'題名','abstract_ja':'要旨','translation':{f:{'hash':fingerprint(r[f],model)} for f in ('title','abstract')}}

class CloudDailyTests(unittest.TestCase):
    def test_public_state_never_retains_pending_text_or_stale_translations(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);a=row(1);b=row(2,'pending')
            write(work/'inbox.json',[a,b]);write(work/'translated.json',[translated(a),translated(b),translated(row(3))])
            write(work/'translation-retries.json',{'10.1234/1':{},'10.1234/2':{}})
            cloud.sanitize(work,NOW)
            self.assertEqual([r['id'] for r in load(work/'inbox.json')],['10.1234/1'])
            self.assertEqual([r['id'] for r in load(work/'translated.json')],['10.1234/1'])
            self.assertEqual(set(load(work/'translation-retries.json')) ,{'10.1234/1'})

    def test_queue_skips_published_cached_and_deferred_and_orders_journals_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);rows=[row(i) for i in range(1,7)];rows[5]['preprint']=True
            write(work/'inbox.json',rows+[row(7,'pending')]);write(work/'translated.json',[translated(rows[1])])
            h=hashlib.sha256((rows[2]['title']+'\n'+rows[2]['abstract']+'|test').encode()).hexdigest()
            write(work/'translation-retries.json',{'10.1234/3':{'input_hash':h,'next_retry':(NOW+dt.timedelta(days=1)).isoformat()}})
            with patch.object(auto,'archive_index',return_value={'issues':[{'doi_keys':['10.1234/1']}]}):
                queue=cloud.pending_rows(work,NOW,'test')
            self.assertEqual([r['id'] for r in queue],['10.1234/4','10.1234/5','10.1234/6'])
            rows[1]['abstract']='Changed marine microbial abstract';write(work/'inbox.json',rows)
            with patch.object(auto,'archive_index',return_value={'issues':[]}):
                self.assertIn('10.1234/2',[r['id'] for r in cloud.pending_rows(work,NOW,'test')])

    def test_state_roundtrip_detects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';repo=root/'repo';remote=root/'remote.git';work.mkdir();repo.mkdir()
            subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
            subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
            subprocess.run(['git','-C',str(repo),'remote','add','origin',str(remote)],check=True)
            write(work/'inbox.json',[row(1)]);write(work/'translated.json',[translated(row(1))])
            cloud.save_state(work,repo,NOW)
            restored=root/'restored';cloud.restore_state(restored,repo)
            self.assertEqual(load(restored/'translated.json'),load(work/'translated.json'))
            write(repo/'state/translated.json',[])
            with self.assertRaisesRegex(RuntimeError,'hash mismatch'):cloud.restore_state(root/'invalid',repo)

    def test_schedule_jitter_does_not_skip_the_next_daily_window(self):
        cfg={'collect_interval_hours':24,'publish_hour_jst':9}
        last=dt.datetime(2026,11,7,0,28,tzinfo=dt.timezone.utc)
        self.assertTrue(cloud.collection_due(last.isoformat(),last+dt.timedelta(days=1,minutes=-11),cfg))
        self.assertFalse(cloud.collection_due(last.isoformat(),last+dt.timedelta(hours=6),cfg))
        self.assertFalse(cloud.collection_due(last.isoformat(),last+dt.timedelta(hours=18),cfg))
        # A recovery at 03:43 belongs to the previous 09:00 publication day.
        recovery=dt.datetime(2026,11,8,18,43,tzinfo=dt.timezone.utc)
        self.assertTrue(cloud.collection_due(recovery.isoformat(),dt.datetime(2026,11,9,0,17,tzinfo=dt.timezone.utc),cfg))

    def test_partial_collection_advances_daily_cursor_but_timeout_does_not(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);old=(NOW-dt.timedelta(days=2)).isoformat()
            write(work/'inbox.json',[row(1)]);write(work/'auto-state.json',{'last_local_collect':old})
            write(str(work/'inbox.json')+'.report.json',{'coverage':{'ok':{'ok':True},'blocked':{'ok':False}}})
            cfg={'collection_timeout_seconds':10,'model':'test'}
            with patch.object(cloud.subprocess,'run',return_value=SimpleNamespace(returncode=2)),patch.object(cloud,'pending_rows',return_value=[]):
                cloud.prepare(work,NOW,cfg)
            self.assertEqual(load(work/'auto-state.json')['last_local_collect'],NOW.isoformat())
            with patch.object(cloud.subprocess,'run') as command,patch.object(cloud,'pending_rows',return_value=[]):
                cloud.prepare(work,NOW+dt.timedelta(hours=6),cfg)
                command.assert_not_called()
            write(work/'auto-state.json',{'last_local_collect':old})
            with patch.object(cloud.subprocess,'run',side_effect=subprocess.TimeoutExpired('collect',10)),patch.object(cloud,'pending_rows',return_value=[]):
                cloud.prepare(work,NOW,cfg)
            self.assertEqual(load(work/'auto-state.json')['last_local_collect'],old)
            self.assertEqual(load(work/'cloud-status.json')['collection_exit_code'],'timeout')

    def test_publication_appends_only_fresh_allowed_translations(self):
        import shutil
        project=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir();(root/'scripts').mkdir()
            shutil.copytree(project/'config',root/'config')
            for name in ('build_issue.py','common.py','journal_catalog.py','topic_filter.py'):
                shutil.copyfile(project/'scripts'/name,root/'scripts'/name)
            a=row(1);b=row(2,'pending');c=row(3);d=row(4)
            write(work/'journal-catalog.json',[]);write(work/'inbox.json',[a,b,c]);write(work/'translated.json',[translated(a),translated(b),translated(c)])
            c['abstract']='Changed marine microbial ecology';write(work/'inbox.json',[a,b,c])
            with patch.object(cloud,'ROOT',root),patch.object(auto,'ROOT',root):
                self.assertEqual(cloud.publish(work,NOW,'test'),'built')
                first=auto.read_front_issue();self.assertEqual([p['id'] for p in first['papers']],[a['id']])
                write(work/'inbox.json',[a,b,c,d]);write(work/'translated.json',[translated(a),translated(b),translated(d)])
                self.assertEqual(cloud.publish(work,NOW,'test'),'already_built')
                self.assertEqual(cloud.publish(work,NOW+dt.timedelta(days=1),'test'),'built')
                second=auto.read_front_issue();self.assertEqual(second['papers'][:1],first['papers'])
                self.assertEqual(second['choice_context'],first['choice_context'])
                self.assertEqual(second['papers'][1]['id'],d['id'])

    def test_eligibility_rejects_translated_pending_papers(self):
        self.assertEqual(auto.eligible([translated(row(1,'pending'))],set(),NOW,45),[])
        self.assertEqual(len(auto.eligible([translated(row(1))],set(),NOW,45)),1)

if __name__=='__main__':unittest.main()
