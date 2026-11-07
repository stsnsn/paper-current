import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_explorer import build,extract_terms
from common import write

class ExplorerTests(unittest.TestCase):
    def test_phrases_and_repeated_terms_are_document_occurrences(self):
        rows=[{'title':'SAR11 and dissolved organic matter','abstract':'SAR11 dissolved organic matter in marine waters.'}]
        terms=extract_terms(rows)[0]
        self.assertIn('dissolved organic matter',terms)
        self.assertEqual(terms.count('SAR11'),1)
        self.assertNotIn('and',terms)

    def test_search_includes_archive_recent_future_and_untranslated_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/'docs/data';base.mkdir(parents=True)
            a={'id':'10.1234/a','doi':'10.1234/a','date':'2026-01-01','title':'SAR11','abstract':'Dissolved organic matter','license':'unknown'}
            b={'id':'10.1234/b','doi':'10.1234/b','date':'2027-01-01','title':'Future SAR11','abstract':'Marine life'}
            write(base/'issues/week.json',{'papers':[a]})
            write(base/'archive-index.json',{'issues':[{'id':'2026-W01','path':'data/issues/week.json'}]})
            (base/'recent-papers.js').write_text('window.PAPER_RECENT_DATA = '+json.dumps([a,b])+';')
            result=build(root);self.assertEqual(result['count'],2);self.assertEqual(len(result['years']),2)
            for entry in result['years']:
                rows=json.loads((root/'docs'/entry['path']).read_text());self.assertEqual(len(rows),1);self.assertNotIn('license',rows[0]);self.assertIn('terms',rows[0])
            before=[e['path'] for e in result['years']];self.assertEqual(before,[e['path'] for e in build(root)['years']])
