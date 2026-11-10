import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from topic_filter import classify
from rss_records import rss_record,merge_record
CFG=json.loads((ROOT/'config/sources.json').read_text())
class TopicFilterTests(unittest.TestCase):
 def test_excluded_journal_overrides_microbiology_relevance(self):
  for journal in ['Frontiers in endocrinology','FRONTIERS IN ENDOCRINOLOGY','Frontiers in Endocrinology (Lausanne)','Front Endocrinol (Lausanne)']:
   decision=classify({'journal':journal,'title':'Marine bacterial microbiome evolution'},CFG)
   self.assertFalse(decision['accepted'],journal)
   self.assertEqual(decision['reason'],'excluded_journal')
  for journal in ['Frontiers in Microbiology','Frontiers in Marine Science']:
   self.assertTrue(classify({'journal':journal,'title':'Marine bacterial microbiome evolution'},CFG)['accepted'],journal)
 def test_frontiers_allowlist_includes_only_two_journals(self):
  for journal in ['Frontiers in Microbiology','frontiers in marine science','Front Microbiol','Front Mar Sci','Frontiers in Microbiology (Lausanne)']:
   self.assertTrue(classify({'journal':journal,'title':'Marine bacterial communities'},CFG)['accepted'],journal)
  for journal in ['Frontiers in Immunology','Frontiers in Genetics','Frontiers in Cellular and Infection Microbiology','Frontiers in Endocrinology','Front Immunol','Front. Genet.','Frontiers in An Unknown New Journal']:
   self.assertFalse(classify({'journal':journal,'title':'Marine bacterial communities'},CFG)['accepted'],journal)
 def test_specialist_and_methods_journals_are_unfiltered(self):
  for journal in ['The ISME Journal','FEMS Yeast Research','Microbes and Environments','Nucleic Acids Research','NAR Genomics and Bioinformatics','Bioinformatics','Microbiology (Reading, England)','Extremophiles : life under extreme conditions']:
   result=classify({'journal':journal,'title':'A new method without organism names'},CFG)
   self.assertTrue(result['accepted'],journal);self.assertEqual(result['reason'],'unfiltered_journal')
 def test_general_and_preprints_need_microbial_evidence(self):
  for title in ['Ocean warming and fish migration','DNA repair in breast cancer','Evolution of galaxies','Microglia in the tumour microenvironment','Archaeology of ancient settlements']:
   for journal,preprint in [('Nature',False)]:
    self.assertFalse(classify({'journal':journal,'preprint':preprint,'title':title},CFG)['accepted'],title)
  for title in ['Marine bacterial evolution','SAR11 DNA repair in the ocean','New fungal genome annotation','Marine microbial communities','16S rRNA profiling','Phage genome host range','Prochlorococcus genome variation']:
   result=classify({'journal':'Science','title':title},CFG);self.assertTrue(result['accepted'],title)
  self.assertTrue(classify({'journal':'Nature','title':'Ocean warming','abstract':'We quantify bacterial communities.'},CFG)['accepted'])
  self.assertFalse(classify({'journal':'bioRxiv','preprint':True,'title':'Ocean warming and fish migration'},CFG)['accepted'])
  self.assertFalse(classify({'journal':'bioRxiv','preprint':True,'title':'DNA repair in breast cancer'},CFG)['accepted'])
 def test_methods_scope_and_pending(self):
  for preprint in (True,False):
   for title in ['Homology-aware average nucleotide identity estimation at scale with a new algorithm','A method for average amino acid identity','Genome annotation in marine protists','Pangenome reconstruction for yeast']:
    self.assertTrue(classify({'title':title,'journal':'Example','preprint':preprint},CFG)['accepted'],title)
   for title in ['A genome pipeline for breast cancer','Ocean warming and fish migration']:
    self.assertFalse(classify({'title':title,'abstract':'We study human disease.','preprint':preprint},CFG)['accepted'])
  self.assertEqual(classify({'title':'Novel computational pipeline'},CFG)['reason'],'metadata_pending')
  self.assertFalse(classify({'title':'Correction: average nucleotide identity estimation'},CFG)['accepted'])
  self.assertFalse(classify({'title':'Human genome analysis','abstract':'Average nucleotide identity is a background concept. We study human disease.'},CFG)['accepted'])
  row={'title':'No taxon names','abstract':'Full text','discovery':[{'source':'test','scope':'target','query':'TITLE_ABS:microbial'}]}
  self.assertTrue(classify(row,CFG)['accepted'])

 def test_context_terms_are_retained_and_reasons_are_reproducible(self):
  row={'journal':'Nature','title':'Evolution of marine bacterial DNA'};r=classify(row,CFG)
  self.assertEqual(r,classify(row,CFG));self.assertIn('海洋微生物',r['tags']);self.assertIn('微生物ゲノミクス',r['tags']);self.assertIn('微生物進化',r['tags'])
 def test_rss_abstract_is_preserved_without_inventing_rights(self):
  url=next(u for u,name in CFG['feed_journals'].items() if name=='Nature')
  row=rss_record({'title':'Ocean change','summary':'<p>Marine bacterial communities shift.</p>','link':'https://doi.org/10.1234/test'},url,CFG)
  self.assertTrue(row['topic_filter']['accepted']);self.assertEqual(row['abstract'],'Marine bacterial communities shift.');self.assertNotIn('rights_status',row);self.assertEqual(row['journal'],'Nature')
 def test_sparse_rss_does_not_erase_api_metadata(self):
  before={'id':'x','title':'Title','abstract':'Full abstract','abstract_source':'Europe PMC','journal':'mBio','rights_status':'allowed','license':'CC BY','title_ja':'題','abstract_ja':'要旨','sources':['Europe PMC']}
  row={'id':'x','title':'Title','abstract':'','journal':'','rights_status':'pending','abstract_source':'rss'}
  merged=merge_record(before,row,'https://example.com/feed')
  self.assertEqual(merged['abstract'],'Full abstract');self.assertEqual(merged['abstract_ja'],'要旨');self.assertNotIn('rights_status',merged)
if __name__=='__main__':unittest.main()
