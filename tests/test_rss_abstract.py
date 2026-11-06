import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rss_records import rss_abstract,NATURE_RSS_JOURNALS,merge_record,normalize_rss_record,rss_record

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

    def test_saved_flattened_rss_is_cleaned_and_stale_translation_removed(self):
        identifier='10.1038/example-2'
        for journal in NATURE_RSS_JOURNALS:
            old=dict(journal=journal,doi=identifier,abstract_source='rss',
                abstract=f'{journal}, Published online: 04 November 2026; doi:{identifier}A bacterial study.',
                abstract_ja='古いヘッダーを含む訳',title_ja='タイトル',translation={'model':'test'},translation_label='old')
            cleaned=normalize_rss_record(old)
            self.assertEqual(cleaned['abstract'],'A bacterial study.')
            self.assertNotIn('abstract_ja',cleaned)
            self.assertNotIn('translation',cleaned)
            self.assertNotIn('translation_label',cleaned)
            self.assertEqual(cleaned['title_ja'],'タイトル')
            self.assertEqual(normalize_rss_record(cleaned),cleaned)
            self.assertIn('Published online:',old['abstract'])

    def test_rss_ingestion_cleans_before_saving_without_id_allowlist(self):
        url='https://example.org/rss'
        for journal in NATURE_RSS_JOURNALS:
            row=rss_record({'title':'Bacterial study','prism_doi':'10.1038/new-doi',
                'summary':f'<p>{journal}, Published online: today; doi:10.1038/new-doi</p><p>Bacteria evolve.</p>'},
                url,{'feed_journals':{url:journal}})
            self.assertEqual(row['abstract'],'Bacteria evolve.')

    def test_metadata_only_saved_row_does_not_restore_old_header(self):
        old=dict(journal='Science',abstract_source='rss',abstract='Science, Volume 394, Issue 6824, November 2026.',abstract_ja='巻号情報')
        result=merge_record(old,dict(journal='Science',abstract_source='rss',abstract=''),'https://example.org/rss')
        self.assertEqual(result['abstract'],'')
        self.assertNotIn('abstract_ja',result)

    def test_api_metadata_and_clean_translations_are_preserved(self):
        for source in ('Europe PMC','rss'):
            row=dict(journal='Nature',abstract_source=source,abstract='Bacteria evolve.',abstract_ja='細菌が進化する。')
            self.assertEqual(normalize_rss_record(row),row)

    def test_replaced_abstract_does_not_inherit_old_translation(self):
        before=dict(title='Study',abstract='Old abstract.',abstract_source='rss',abstract_ja='古い訳',translation_label='old')
        row=dict(title='Study',abstract='New abstract.',abstract_source='rss')
        result=merge_record(before,row,'https://example.org/rss')
        self.assertNotIn('abstract_ja',result)
        self.assertNotIn('translation_label',result)

if __name__=='__main__':unittest.main()
