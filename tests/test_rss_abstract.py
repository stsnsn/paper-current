import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rss_records import rss_abstract,NATURE_RSS_JOURNALS,merge_record

class RSSAbstractTests(unittest.TestCase):
    def test_nature_html_boundaries_preserve_first_body_character(self):
        for journal in NATURE_RSS_JOURNALS:
            raw=f'<p>{journal}, Published online: 04 November 2026; doi:10.1038/example-2</p><p>A clinical trial tested bacteria.</p>'
            self.assertEqual(rss_abstract(raw,journal),'A clinical trial tested bacteria.')
            self.assertEqual(rss_abstract('<p>Full abstract without a metadata header.</p>',journal),'Full abstract without a metadata header.')

    def test_pnas_prefix_and_full_api_abstract_preference(self):
        raw='Proceedings of the National Academy of Sciences, Volume 123, Issue 44, November 2026. SignificanceBacteria ...'
        self.assertEqual(rss_abstract(raw,'PNAS'),'SignificanceBacteria ...')
        before={'abstract':'Complete abstract.','abstract_source':'Europe PMC','sources':[]}
        row={'abstract':rss_abstract(raw,'PNAS'),'abstract_source':'rss'}
        self.assertEqual(merge_record(before,row,'https://example.org/rss')['abstract'],'Complete abstract.')

    def test_metadata_only_is_not_an_abstract(self):
        for journal in ('Science','Science Advances'):
            self.assertEqual(rss_abstract(f'{journal}, Volume 394, Issue 6824, November 2026.',journal),'')
        raw='<p>Publication date: February 2027</p><p>Source: Molecular Phylogenetics and Evolution, Volume 227</p><p>Author(s): A. Author</p>'
        self.assertEqual(rss_abstract(raw,'Molecular Phylogenetics and Evolution'),'')
        self.assertEqual(rss_abstract(raw+'<p>Actual bacterial abstract.</p>','Molecular Phylogenetics and Evolution'),'Actual bacterial abstract.')

    def test_other_journals_are_unchanged(self):
        raw='<p>In this issue of Cell Reports, we study bacteria.</p>'
        self.assertEqual(rss_abstract(raw,'Cell Reports'),'In this issue of Cell Reports, we study bacteria.')

if __name__=='__main__':unittest.main()
