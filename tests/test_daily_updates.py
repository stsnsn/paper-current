import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from test_automation import paper,PROJECT
import test_archives
import auto
from common import load,write

class DailyUpdates(unittest.TestCase):
    def prepare(self,root):
        shutil.copytree(PROJECT/'config',root/'config')
        (root/'scripts').mkdir()
        for f in ('build_issue.py','common.py','journal_catalog.py','topic_filter.py','topic_scope.py'):
            shutil.copy(PROJECT/'scripts'/f,root/'scripts'/f)
        work=root/'work';work.mkdir(exist_ok=True)
        return work,load(PROJECT/'config/automation.json')

    def test_addition_history_sums_batches_and_survives_week_rollover(self):
        now=dt.datetime(2026,11,8,23,tzinfo=auto.JST)
        first=auto.addition_history(None,[paper(1)],now)
        second=auto.addition_history({'issue':first},[paper(2)],now+dt.timedelta(hours=2))
        self.assertEqual(len(second['addition_history']),2)
        self.assertEqual(second['addition_tracking_since'],now.isoformat())
        self.assertEqual(second['addition_history'][0]['papers'][0]['id'],'1')
        third=auto.addition_history({'issue':second},[paper(3)],now+dt.timedelta(hours=49))
        self.assertEqual(len(third['addition_history']),2)
        self.assertEqual(third['addition_tracking_since'],now.isoformat())

    def test_daily_append_rollover_and_delayed_translations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work,cfg=self.prepare(root);state={}
            monday=dt.datetime(2026,11,9,1,tzinfo=dt.timezone.utc)
            write(work/'translated.json',[paper(1)])
            with patch.object(auto,'ROOT',root):
                self.assertEqual(auto.build_week(cfg,work,state,monday.replace(hour=23)-dt.timedelta(days=1)),'not_due')
                self.assertEqual(auto.build_week(cfg,work,state,monday),'built')
                first=load(root/'docs/data/issues/2026-W46.json')
                self.assertEqual(len(first['papers']),1)
                write(work/'translated.json',[paper(1),paper(2)])
                self.assertEqual(auto.build_week(cfg,work,state,monday+dt.timedelta(hours=2)),'built')
                self.assertEqual(auto.build_week(cfg,work,state,monday+dt.timedelta(days=1)),'waiting')
                second=load(root/'docs/data/issues/2026-W46.json')
                self.assertEqual(second['papers'][:1],first['papers'])
                self.assertEqual(second['choice_context'],first['choice_context'])
                self.assertEqual(second['issue']['added_ids'],['10.1234/2'])
                # Identical data does not rewrite the issue on the next day.
                before=(root/'docs/data/papers.js').read_bytes()
                self.assertEqual(auto.build_week(cfg,work,state,monday+dt.timedelta(days=2)),'waiting')
                self.assertEqual(before,(root/'docs/data/papers.js').read_bytes())
                # A late translation belongs to its first publication week.
                write(work/'translated.json',[paper(1),paper(2),paper(3)])
                self.assertEqual(auto.build_week(cfg,work,state,monday+dt.timedelta(days=7)),'built')
                third=load(root/'docs/data/issues/2026-W47.json')
                self.assertEqual([p['id'] for p in third['papers']],['10.1234/3'])
                self.assertEqual(load(root/'docs/data/issues/2026-W46.json'),second)
                self.assertEqual(load(root/'docs/data/archive-index.json')['archive_policy'],'weekly')

    def test_current_payload_can_be_recovered_from_front_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work,cfg=self.prepare(root);state={}
            now=dt.datetime(2026,11,9,1,tzinfo=dt.timezone.utc)
            with patch.object(auto,'ROOT',root):
                write(work/'translated.json',[paper(1)])
                auto.build_week(cfg,work,state,now)
                path=root/'docs/data/issues/2026-W46.json';first=load(path)
                path.unlink()
                write(work/'translated.json',[paper(1),paper(2)])
                self.assertEqual(auto.build_week(cfg,work,state,now+dt.timedelta(days=1)),'built')
                self.assertEqual(load(path)['papers'][:1],first['papers'])

    def test_interrupted_publication_repairs_front_and_index_without_new_papers(self):
        for append in (False,True):
            for failure in ('front','index'):
                with self.subTest(append=append,failure=failure),tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp);work,cfg=self.prepare(root);state={}
                    now=dt.datetime(2026,11,9,1,tzinfo=dt.timezone.utc)
                    with patch.object(auto,'ROOT',root):
                        write(work/'translated.json',[paper(1)])
                        if append:auto.build_daily(cfg,work,state,now)
                        write(work/'translated.json',[paper(1),paper(2)] if append else [paper(1)])
                        real_write=auto.write
                        def fail_index(path,value):
                            if Path(path).name=='archive-index.json':raise OSError('index interrupted')
                            return real_write(path,value)
                        interruption=(patch.object(Path,'replace',side_effect=OSError('front interrupted'))
                            if failure=='front' else patch.object(auto,'write',side_effect=fail_index))
                        with interruption,self.assertRaises(OSError):
                            auto.build_daily(cfg,work,state,now+dt.timedelta(hours=1))
                        path=root/'docs/data/issues/2026-W46.json'
                        canonical=load(path)
                        self.assertEqual(auto.build_daily(cfg,work,state,now+dt.timedelta(hours=2)),'recovered')
                        entry=auto.archive_index()['issues'][0]
                        self.assertEqual(entry['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
                        self.assertEqual(entry['count'],2 if append else 1)
                        self.assertEqual(auto.read_front_issue(),canonical)
                        self.assertEqual(load(path),canonical)
                        before=(root/'docs/data/archive-index.json').read_bytes()
                        self.assertEqual(auto.build_daily(cfg,work,state,now+dt.timedelta(hours=3)),'waiting')
                        self.assertEqual((root/'docs/data/archive-index.json').read_bytes(),before)

    def test_missing_current_payload_is_recovered_without_additions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work,cfg=self.prepare(root);state={}
            now=dt.datetime(2026,11,9,1,tzinfo=dt.timezone.utc)
            with patch.object(auto,'ROOT',root):
                write(work/'translated.json',[paper(1)])
                auto.build_daily(cfg,work,state,now)
                path=root/'docs/data/issues/2026-W46.json';original=path.read_bytes();path.unlink()
                self.assertEqual(auto.build_daily(cfg,work,state,now+dt.timedelta(hours=1)),'recovered')
                self.assertEqual(path.read_bytes(),original)

    def test_revision_push_retry_and_frozen_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,remote=test_archives.ArchiveTests().setup_repo(Path(tmp));work,cfg=self.prepare(root);state={}
            now=dt.datetime(2026,11,9,1,tzinfo=dt.timezone.utc)
            with patch.object(auto,'ROOT',root):
                write(work/'translated.json',[paper(1)])
                auto.publish_week(cfg,work,state,now,push=True)
                path=root/'docs/data/issues/2026-W46.json'
                self.assertTrue(path.exists())
                original=load(path)
                write(work/'translated.json',[paper(1),paper(2)])
                auto.build_week(cfg,work,state,now+dt.timedelta(days=1))
                # Failure retains the revision and its published base hash.
                good_hash=state['pushed_hashes']['2026-W46']
                with patch.object(auto,'command',side_effect=RuntimeError('offline')):
                    with self.assertRaises(RuntimeError):auto.push_pending(cfg,work,state,now+dt.timedelta(days=1))
                self.assertTrue(path.exists());self.assertEqual(state['pushed_hashes']['2026-W46'],good_hash)
                auto.push_pending(cfg,work,state,now+dt.timedelta(days=1))
                remote_data=json.loads(subprocess.run(['git','--git-dir',str(remote),'show','main:docs/data/issues/2026-W46.json'],check=True,capture_output=True,text=True).stdout)
                self.assertEqual(len(remote_data['papers']),2)
                self.assertEqual(remote_data['papers'][:1],original['papers'])
                # A no-op retry creates no extra commit.
                auto.push_pending(cfg,work,state,now+dt.timedelta(days=1))
                # Past-week changes are rejected even when append-only.
                data=load(path);data['papers'].append(paper(3));write(path,data)
                index=load(root/'docs/data/archive-index.json');index['issues'][0]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();write(root/'docs/data/archive-index.json',index)
                with self.assertRaisesRegex(RuntimeError,'already exists'):
                    auto.push_pending(cfg,work,state,now+dt.timedelta(days=7))
                self.assertTrue(path.exists())

    def test_remote_current_papers_cannot_be_reordered_or_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,remote=test_archives.ArchiveTests().setup_repo(Path(tmp));work,cfg=self.prepare(root);state={}
            now=dt.datetime(2026,11,9,1,tzinfo=dt.timezone.utc)
            with patch.object(auto,'ROOT',root):
                write(work/'translated.json',[paper(1)])
                auto.publish_week(cfg,work,state,now,push=True)
                write(work/'translated.json',[paper(1),paper(2)])
                auto.build_week(cfg,work,state,now+dt.timedelta(days=1))
                path=root/'docs/data/issues/2026-W46.json';data=load(path);data['papers'][0]['title']='changed';write(path,data)
                index=load(root/'docs/data/archive-index.json');index['issues'][0]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();write(root/'docs/data/archive-index.json',index)
                with self.assertRaisesRegex(RuntimeError,'only append'):
                    auto.push_pending(cfg,work,state,now+dt.timedelta(days=1))

if __name__=='__main__':unittest.main()
