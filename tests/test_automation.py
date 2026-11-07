import datetime as dt
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'scripts'))
import auto
from common import load,write
from translate import translate_records

class FakeTranslator:
    model='plamo-test'
    def __init__(self):self.calls=[];self.fail=True
    def translate(self,text):
        self.calls.append(text)
        if text=='abstract-1' and self.fail:raise RuntimeError('temporary outage')
        return '訳:'+text

def paper(i):
    return {'id':str(i),'title':f'title-{i}','abstract':f'abstract-{i}',
        'rights_status':'allowed','doi':f'10.1234/{i}','journal':'mBio',
        'date':'2026-11-08','tags':['海洋微生物'],'title_ja':'題名','abstract_ja':'要旨'}

class AutomationTests(unittest.TestCase):
    def test_legacy_rights_do_not_block_translation_or_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            row=paper(1);row['rights_status']='pending';out=Path(tmp)/'out.json'
            translator=FakeTranslator();translator.fail=False
            stats=translate_records([row],out,translator)
            self.assertEqual(stats['translated'],1)
            translated=load(out)[0];self.assertNotIn('rights_status',translated)
            self.assertEqual(len(auto.eligible([translated],set(),dt.datetime(2026,11,9,tzinfo=dt.timezone.utc),45)),1)
            row.pop('abstract');row['id']='title-only';row['doi']='10.1234/title-only'
            stats=translate_records([row],out,translator,include_pending=True)
            title_only=next(p for p in load(out) if p['doi']==row['doi'])
            self.assertEqual(stats['translated'],1);self.assertTrue(title_only['title_ja']);self.assertNotIn('abstract_ja',title_only)
    def test_review_is_eligible_with_translations_and_rights(self):
        row=paper(1);row['review']=True
        now=dt.datetime(2026,11,9,tzinfo=dt.timezone.utc)
        eligible=auto.eligible([row],set(),now,45)
        self.assertEqual(len(eligible),1);self.assertTrue(eligible[0]['review'])
        row['rights_status']='pending'
        self.assertEqual(len(auto.eligible([row],set(),now,45)),1)
        row['rights_status']='allowed'
        for field in ('title','abstract','title_ja','abstract_ja'):
            incomplete=dict(row);incomplete[field]=''
            self.assertEqual(auto.eligible([incomplete],set(),now,45),[])
        self.assertEqual(auto.eligible([row],set(),now+dt.timedelta(days=46),45),[])
        excluded=dict(row,topic_filter={'accepted':False})
        self.assertEqual(auto.eligible([excluded],set(),now,45),[])

    def test_partial_failure_cooldown_resume_and_input_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'translations.json';retry=Path(tmp)/'retry.json';t=FakeTranslator()
            now=dt.datetime(2026,11,9,tzinfo=dt.timezone.utc)
            rows=[paper(1),paper(2)]
            stats=translate_records(rows,out,t,keep_going=True,retry_state=retry,now=now)
            self.assertEqual(stats['failed'],1);self.assertEqual(stats['translated'],1)
            saved={x['id']:x for x in load(out)}
            self.assertEqual(saved['10.1234/1']['title_ja'],'訳:title-1');self.assertNotIn('abstract_ja',saved['10.1234/1'])
            self.assertEqual(saved['10.1234/2']['abstract_ja'],'訳:abstract-2')
            count=len(t.calls)
            stats=translate_records(rows,out,t,keep_going=True,retry_state=retry,now=now+dt.timedelta(minutes=1))
            self.assertEqual(stats['deferred'],1);self.assertEqual(len(t.calls),count)
            t.fail=False
            translate_records(rows,out,t,keep_going=True,retry_state=retry,now=now+dt.timedelta(minutes=16))
            self.assertEqual(t.calls[-1],'abstract-1');self.assertEqual(t.calls.count('title-1'),1)
            self.assertEqual(load(retry),{})
            rows[1]['abstract']='revised-abstract'
            count=len(t.calls)
            translate_records(rows,out,t,keep_going=True,retry_state=retry,now=now+dt.timedelta(minutes=17))
            self.assertEqual(t.calls[count:],['revised-abstract'])

    def test_batch_limit_has_bounded_writes_and_refreshes_all_metadata(self):
        import translate as module
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out.json';translator=FakeTranslator();translator.fail=False
            rows=[paper(i) for i in range(100)]
            with patch.object(module,'write',wraps=write) as writes:
                translate_records(rows,out,translator,limit=2)
                self.assertEqual(sum(call.args[0]==out for call in writes.call_args_list),5)
            self.assertEqual(len(load(out)),100)
            # A cached second pass must not rewrite every cached record.
            with patch.object(module,'write',wraps=write) as writes:
                translate_records(rows,out,translator,limit=2)
                self.assertEqual(sum(call.args[0]==out for call in writes.call_args_list),4)
            rows[0]['rights_status']='pending'
            translate_records(rows,out,translator,limit=1)
            self.assertNotIn('rights_status',next(row for row in load(out) if row['doi']==rows[0]['doi']))

    def test_limit_does_not_starve_later_papers(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out.json';t=FakeTranslator();t.fail=False
            rows=[paper(i) for i in range(4)]
            translate_records(rows,out,t,limit=2)
            self.assertEqual(len(t.calls),4)
            translate_records(rows,out,t,limit=2)
            self.assertEqual(len(t.calls),8)
            self.assertTrue(all(a.get('abstract_ja') for a in load(out)))

    def test_week_is_frozen_and_no_repeat_next_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir()
            shutil.copytree(PROJECT/'config',root/'config')
            (root/'scripts').mkdir()
            for f in ('build_issue.py','common.py','journal_catalog.py','topic_filter.py'):shutil.copy(PROJECT/'scripts'/f,root/'scripts'/f)
            (root/'docs/data').mkdir(parents=True)
            rows=[paper(i) for i in range(6)];write(work/'translated.json',rows)
            cfg=load(PROJECT/'config/automation.json');cfg['publication_mode']='weekly';cfg['minimum_questions']=5;state={}
            now=dt.datetime(2026,11,9,1,tzinfo=dt.timezone.utc)
            with patch.object(auto,'ROOT',root):
                self.assertEqual(auto.publish_week(cfg,work,state,now),'built')
                initial=(root/'docs/data/papers.js').read_bytes()
                write(work/'translated.json',rows+[paper(99)])
                self.assertEqual(auto.publish_week(cfg,work,state,now),'already_built')
                self.assertEqual(initial,(root/'docs/data/papers.js').read_bytes())
                # Archived payload can be absent locally; DOI index still blocks repeats.
                (root/'docs/data/issues/2026-W46.json').unlink()
                auto.publish_week(cfg,work,state,now)
                self.assertEqual(initial,(root/'docs/data/papers.js').read_bytes())
                self.assertEqual(auto.publish_week(cfg,work,state,now+dt.timedelta(days=7)),'waiting')

    def test_offline_lm_keeps_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);write(work/'inbox.json',[paper(1)])
            cfg=load(PROJECT/'config/automation.json');cfg['source']='local'
            with patch.object(auto,'collect_local',return_value=False),patch.object(auto.Translator,'connect',side_effect=ConnectionError('LM offline')),patch.object(auto,'publish_week',return_value='waiting'),self.assertLogs(auto.LOG,level='ERROR'):
                auto.cycle(cfg,work,{},dt.datetime(2026,11,9,tzinfo=dt.timezone.utc))
            self.assertEqual(len(load(work/'inbox.json')),1);self.assertEqual(load(work/'status.json')['collected'],1)

if __name__=='__main__':unittest.main()
