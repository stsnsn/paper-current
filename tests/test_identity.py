import copy
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from common import doi,dedupe_records,paper_keys,write
from auto import eligible
from translate import translate_records

class IdentityTests(unittest.TestCase):
    def test_doi_url_case_encoding_and_preprint_versions(self):
        for value in ('DOI:10.1234/ABC','https://doi.org/10.1234/ABC','https://doi.org/10.1234%2FABC?x=1'):
            self.assertEqual(doi(value),'10.1234/abc')
        for prefix in ('10.1101','10.64898'):
            self.assertEqual(doi(f'https://www.biorxiv.org/content/{prefix}/2026.01.01.123456v3.full.pdf'),f'{prefix}/2026.01.01.123456')

    def test_versions_merge_and_explicit_publication_link_is_transitive(self):
        old={'id':'old','doi':'10.64898/2026.01.01.123456v1','version':'1','preprint':True,'abstract':'v1','rights_status':'allowed'}
        new={**old,'doi':'10.64898/2026.01.01.123456','version':'2','abstract':'v2','published_doi':'https://doi.org/10.1234/PUB'}
        article={'id':'article','doi':'10.1234/pub','journal':'mBio','abstract':'published','rights_status':'allowed'}
        rows=dedupe_records([old,article,new])
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['abstract'],'published')
        self.assertIn('10.64898/2026.01.01.123456',paper_keys(rows[0]));self.assertIn('10.1234/pub',paper_keys(rows[0]))
        self.assertEqual(dedupe_records([old,new])[0]['abstract'],'v2')

    def test_different_dois_not_merged_by_title(self):
        rows=dedupe_records([{'id':'x','doi':'10.1234/a','title':'Same title'},{'id':'y','doi':'10.1234/b','title':'Same title'}])
        self.assertEqual(len(rows),2)

    def test_preprint_is_a_question_but_has_no_fabricated_correct_answer(self):
        row=copy.deepcopy(json.loads((ROOT/'docs/data/demo.json').read_text())[0])
        self.assertTrue(row['preprint'])
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'in.json';out=Path(tmp)/'out.js';write(src,[row,{**row,'doi':row['doi']+'v3','id':'duplicate','version':'3'}])
            subprocess.run([sys.executable,str(ROOT/'scripts/build_issue.py'),str(src),'--out',str(out)],check=True,capture_output=True)
            data=json.loads(out.read_text().removeprefix('window.PAPER_DATA = ').strip().rstrip(';'))
            self.assertEqual(len(data['papers']),1);paper=data['papers'][0]
            self.assertEqual(paper['question_type'],'forecast');self.assertIsNone(paper['answer_journal'])
            self.assertEqual(len(set(paper['options'])),4);self.assertNotIn('bioRxiv',paper['options'])

    def test_prior_preprint_blocks_repeat_after_publication(self):
        row=copy.deepcopy(json.loads((ROOT/'docs/data/demo.json').read_text())[0]);row['published_doi']='10.1234/pub';row['date']='2026-11-06'
        used={doi(row['doi'])}
        self.assertEqual(eligible([row],used,dt.datetime(2026,11,6),45),[])
        self.assertEqual(len(eligible([row],set(),dt.datetime(2026,11,6),45)),1)

    def test_duplicate_doi_does_not_trigger_duplicate_translation(self):
        class Translator:
            model='test'
            def __init__(self):self.calls=[]
            def translate(self,s):self.calls.append(s);return '訳'
        t=Translator();row={'id':'1','doi':'10.1234/ABC','title':'Title','abstract':'Abstract','rights_status':'allowed'}
        with tempfile.TemporaryDirectory() as tmp:
            translate_records([row,{**row,'id':'2','doi':'https://doi.org/10.1234/abc'}],Path(tmp)/'out.json',t)
        self.assertEqual(len(t.calls),2)

if __name__=='__main__':unittest.main()
