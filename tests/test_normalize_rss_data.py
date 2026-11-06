import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import load,write
from normalize_rss_data import repair_record,migrate
from translate import fingerprint

class RSSDataMigration(unittest.TestCase):
    def nature(self):
        identifier='10.1038/new-paper'
        row=dict(id=identifier,doi=identifier,journal='Nature',abstract_source='rss',
            abstract=f'Nature, Published online: today; doi:{identifier}A bacterial study.',
            abstract_ja=f'Nature, オンライン公開：本日; doi:{identifier}細菌の研究。',
            translation={'abstract':{'hash':'old','model':'test'}})
        row['translation']['abstract']['hash']=fingerprint(row['abstract'],'test')
        return row

    def test_both_languages_and_cache_are_repaired_without_mutating_input(self):
        row=self.nature();result=repair_record(row)
        self.assertEqual(result['abstract'],'A bacterial study.')
        self.assertEqual(result['abstract_ja'],'細菌の研究。')
        self.assertEqual(result['translation']['abstract']['hash'],fingerprint(result['abstract'],'test'))
        self.assertEqual(row['translation']['abstract']['hash'],fingerprint(row['abstract'],'test'))
        self.assertEqual(repair_record(result),result)

    def test_missing_abstract_and_pnas_japanese_volume(self):
        row=dict(id='new',journal='Science',abstract_source='rss',
            abstract='Science, Volume 394, Issue 6824, November 2026.',abstract_ja='Science誌 第394巻 第6824号 2026年11月。')
        result=repair_record(row)
        self.assertEqual((result['abstract'],result['abstract_ja']),('',''))
        row.update(journal='PNAS',abstract='Proceedings of the National Academy of Sciences, Volume 123, Issue 44, November 2026. Bacteria.',
            abstract_ja='米国科学アカデミー紀要 第123巻 第44号 2026年11月。細菌。')
        row['translation']={'abstract':{'model':'test','hash':fingerprint(row['abstract'],'test')}}
        result=repair_record(row)
        self.assertEqual((result['abstract'],result['abstract_ja']),('Bacteria.','細菌。'))

    def test_stale_or_unverifiable_translation_is_not_given_a_new_hash(self):
        for cache in ({'model':'test','hash':fingerprint('Different abstract.','test')},{},None):
            row=self.nature()
            if cache is None:row.pop('translation')
            else:row['translation']['abstract']=cache
            result=repair_record(row)
            self.assertEqual(result['abstract'],'A bacterial study.')
            self.assertEqual(result['abstract_ja'],'')
            self.assertNotIn('abstract',result.get('translation',{}))
            self.assertEqual(repair_record(result),result)

    def test_unparseable_translated_header_invalidates_only_the_abstract(self):
        row=self.nature();row['abstract_ja']='Nature, オンライン公開：本日。細菌の研究。'
        row['title_ja']='題名';row['translation']['title']={'hash':'title-cache'}
        result=repair_record(row)
        self.assertEqual(result['abstract'],'A bacterial study.')
        self.assertEqual(result['abstract_ja'],'')
        self.assertNotIn('abstract',result['translation'])
        self.assertEqual(result['translation']['title'],{'hash':'title-cache'})
        self.assertEqual(result['title_ja'],'題名')

    def test_migration_updates_archive_hash_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';path=root/'docs/data/issues/example.json'
            data={'issue':{'id':'example'},'papers':[self.nature()]}
            write(path,data);write(root/'docs/data/archive-index.json',{'issues':[{'id':'example','sha256':'old'}]})
            front=root/'docs/data/papers.js';front.write_text('window.PAPER_DATA = '+json.dumps(data)+';\n')
            self.assertTrue(migrate(root,work))
            self.assertEqual(load(path),data)
            self.assertTrue(migrate(root,work,True))
            self.assertEqual(load(root/'docs/data/archive-index.json')['issues'][0]['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(json.loads(front.read_text().split(' = ',1)[1].strip().rstrip(';')),load(path))
            self.assertEqual(migrate(root,work),[])
