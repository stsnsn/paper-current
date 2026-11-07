import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from epmc_metadata import parse_fulltext_metadata,enrich_core
from common import dedupe_records,write,load
from translate import translate_records,fingerprint
XML='''<article><front><article-meta><article-id pub-id-type="pmcid">PMC123</article-id><article-id pub-id-type="pmid">456</article-id><article-id pub-id-type="doi">10.1234/test</article-id><pub-date><day>1</day><month>1</month><year>2026</year></pub-date><pub-date pub-type="epub"><day>20</day><month>10</month><year>2026</year></pub-date><abstract abstract-type="graphical"><p>Not the abstract</p></abstract><abstract><title>Abstract</title><p>Marine <italic>bacteria</italic> matter.</p><sec sec-type="kwd-group"><title>Keywords</title><p>keyword noise</p></sec><sec><title>Supplementary Information</title><p>Download data</p></sec></abstract><permissions><license><license-p>Licensed under https://creativecommons.org/licenses/by/4.0/</license-p></license></permissions></article-meta></front><body><p>Full body must not become abstract.</p></body></article>'''
class EpmcMetadataTests(unittest.TestCase):
 def test_extracts_primary_abstract_identifiers_date_and_license(self):
  result=parse_fulltext_metadata(XML)
  self.assertEqual(result['abstractText'],'Marine bacteria matter.');self.assertEqual(result['doi'],'10.1234/test')
  self.assertEqual(result['pmid'],'456');self.assertEqual(result['firstPublicationDate'],'2026-10-20');self.assertNotIn('license',result)
 def test_fallback_is_cached_and_discards_license_metadata(self):
  calls=[]
  class Response:
   content=XML.encode()
   def raise_for_status(self):pass
  def fetch(url):calls.append(url);return Response()
  with tempfile.TemporaryDirectory() as tmp:
   row={'source':'PMC','id':'PMC123','license':'cc by-nc-nd','firstPublicationDate':'2026-01-01'}
   result=enrich_core(row,fetch,tmp);self.assertNotIn('license',result);self.assertEqual(result['abstract_source'],'Europe PMC fullTextXML')
   self.assertEqual(result['firstPublicationDate'],'2026-10-20')
   self.assertEqual(enrich_core(row,fetch,tmp),result);self.assertEqual(len(calls),1)
   with self.assertRaises(ValueError):enrich_core({**row,'doi':'10.1234/wrong'},fetch,tmp)
 def test_missing_xml_abstract_is_not_replaced_by_body(self):
  self.assertNotIn('abstractText',parse_fulltext_metadata('<article><front><article-meta/></front><body>Not an abstract</body></article>'))
 def test_explicit_identifiers_merge_stub_without_losing_valid_title_cache(self):
  cached={'id':'epmc:PMC:PMC123','title':'Title','title_ja':'題名','translation':{'title':{'hash':'cached','model':'plamo'}},'rights_status':'allowed'}
  full={'id':'10.1234/test','doi':'10.1234/test','pmcid':'PMC123','pmid':'456','title':'Title','abstract':'Full abstract','rights_status':'allowed'}
  result=dedupe_records([cached,full]);self.assertEqual(len(result),1);self.assertEqual(result[0]['id'],'10.1234/test')
  self.assertEqual(result[0]['title_ja'],'題名');self.assertEqual(result[0]['translation']['title']['hash'],'cached')
  self.assertEqual(result[0]['pmcid'],'PMC123')
  changed={**full,'title':'Different title'};self.assertNotIn('title_ja',dedupe_records([cached,changed])[0])
 def test_enriched_doi_reuses_previous_pmc_title_translation(self):
  class Translator:
   model='plamo-test'
   def __init__(self):self.calls=[]
   def translate(self,value):self.calls.append(value);return '訳:'+value
  translator=Translator()
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'translated.json'
   old={'id':'epmc:PMC:PMC123','title':'Title','title_ja':'題名','rights_status':'allowed','translation':{'title':{'hash':fingerprint('Title',translator.model),'model':translator.model}}}
   write(out,[old])
   row={'id':'10.1234/test','doi':'10.1234/test','pmcid':'PMC123','title':'Title','abstract':'Recovered abstract','rights_status':'allowed'}
   translate_records([row],out,translator)
   self.assertEqual(translator.calls,['Recovered abstract']);self.assertEqual(len(load(out)),1);self.assertEqual(load(out)[0]['title_ja'],'題名')
if __name__=='__main__':unittest.main()
