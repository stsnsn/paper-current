import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from journal_catalog import update_catalog,summarize_journals
class JournalCatalogTests(unittest.TestCase):
    def test_accumulates_without_preprint_venue_and_merges_aliases(self):
        old=[{'name':'The ISME Journal','scope':['ecology']}]
        rows=[{'journal':'ISME Journal','tags':['微生物ゲノミクス']},
              {'journal':'bioRxiv','preprint':True,'published_journal':'New Journal','tags':['海洋微生物']}]
        catalog=update_catalog(old,rows)
        self.assertEqual(len(catalog),2)
        self.assertEqual(next(j for j in catalog if j['name']=='The ISME Journal')['scope'],['ecology','genomics','microbiology'])
        self.assertEqual(update_catalog(catalog,[]),catalog)
    def test_rss_source_mapping_recovers_venue_from_earlier_queue(self):
        catalog=update_catalog([], [{'sources':['feed-url'],'tags':['海洋微生物']}], {'feed-url':'New RSS Journal'})
        self.assertEqual(catalog[0]['name'],'New RSS Journal')
        self.assertIn('ecology',catalog[0]['scope'])
    def test_summary_counts_servers_separately_and_uses_rss_mapping(self):
        rows=[{'preprint':True,'journal':'bioRxiv','title':'A','abstract':'B'},
              {'sources':['rss'],'title':'C'}, {'journal':'New Journal','abstract':'D'}]
        summary=summarize_journals(rows,{'rss':'Mapped Journal'})
        self.assertEqual(summary['total'],3)
        self.assertEqual(summary['preprint_servers'],[{'name':'bioRxiv','count':1}])
        self.assertEqual(sum(j['count'] for j in summary['journals']),2)
        self.assertEqual(summary['missing_abstract'],1)
        self.assertEqual(summary['unknown_venue'],0)
    def test_build_embeds_all_candidates_including_untranslated_journals(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);rows=json.loads((ROOT/'docs/data/demo.json').read_text())
            rows.append({'id':'new','doi':'10.1234/new','journal':'New Untranslated Journal','rights_status':'pending','tags':['海洋微生物']})
            (tmp/'in.json').write_text(json.dumps(rows));(tmp/'catalog.json').write_text(json.dumps([{'name':'Previously Seen Journal','scope':['genomics']}]))
            subprocess.run([sys.executable,str(ROOT/'scripts/build_issue.py'),str(tmp/'in.json'),'--journal-catalog',str(tmp/'catalog.json'),'--out',str(tmp/'out.js')],check=True,capture_output=True)
            data=json.loads((tmp/'out.js').read_text().removeprefix('window.PAPER_DATA = ').strip().rstrip(';'))
            names=[j['name'] for j in data['journal_catalog']]
            self.assertIn('New Untranslated Journal',names);self.assertIn('Previously Seen Journal',names)
            self.assertNotIn('new',[p['id'] for p in data['papers']])
if __name__=='__main__':unittest.main()
