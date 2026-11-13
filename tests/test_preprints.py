import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from preprints import arxiv_query,arxiv_record
from topic_filter import classify
from rss_records import rss_record
from common import dedupe_records,has_paper_identifier
CFG=json.loads((ROOT/'config/sources.json').read_text())

class PreprintTests(unittest.TestCase):
    def test_all_servers_require_content_evidence(self):
        for server in ('bioRxiv','EcoEvoRxiv','arXiv'):
            for title in ('Evolution of galaxies','Ocean warming and fish migration','Genomic variation in breast cancer'):
                row=dict(journal=server,preprint=True,title=title,abstract='We study this system.',discovery=[{'scope':'target','query':'marine bacteria'}])
                self.assertFalse(classify(row,CFG)['accepted'],(server,title))
            for title in ('Marine bacterial communities','A new algorithm for metagenome assembly','A database of protein families'):
                self.assertTrue(classify(dict(journal=server,preprint=True,title=title),CFG)['accepted'])

    def test_ecoevorxiv_feed_is_a_filtered_preprint(self):
        url='https://ecoevorxiv.org/rss/preprints/'
        self.assertIn(url,CFG['feeds'])
        row=rss_record({'title':'Fish migration in oceans','summary':'We study fish ecology.','link':'https://doi.org/10.32942/X12345'},url,CFG)
        self.assertTrue(row['preprint']);self.assertEqual(row['journal'],'EcoEvoRxiv')
        self.assertFalse(row['topic_filter']['accepted'])
        row['doi']='';row['source_url']='https://ecoevorxiv.org/repository/view/16054/'
        self.assertTrue(has_paper_identifier(row))
        self.assertFalse(has_paper_identifier({**row,'preprint':False}))

    def test_arxiv_identity_versions_and_publication_alias(self):
        entry={'id':'http://arxiv.org/abs/2611.01234v2','title':'Marine bacterial genomes','summary':'Full abstract','published':'2026-11-01T00:00:00Z','authors':[{'name':'A Author'}]}
        row=arxiv_record(entry,'query');self.assertEqual(row['doi'],'10.48550/arxiv.2611.01234')
        self.assertEqual(row['version'],'2');self.assertEqual(row['discovery'][0]['scope'],'candidate')
        first=arxiv_record({**entry,'id':'http://arxiv.org/abs/2611.01234v1'},'query')
        self.assertEqual(len(dedupe_records([first,row])),1)
        self.assertEqual(dedupe_records([first,row])[0]['version'],'2')
        with self.assertRaises(ValueError):arxiv_record({'id':'http://arxiv.org/api/errors'},'query')

    def test_query_is_date_bounded_and_searches_titles_and_abstracts(self):
        query=arxiv_query('2026-11-01','2026-11-13')
        self.assertIn('lastUpdatedDate:[202611010000 TO 202611132359]',query)
        self.assertIn('ti:"microbial"',query);self.assertIn('abs:"protein"',query)

if __name__=='__main__':unittest.main()
