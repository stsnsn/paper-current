import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import translate_queue
from common import write,load
class TranslationQueueTests(unittest.TestCase):
 def test_round_robin_avoids_one_journal_dominating(self):
  rows=[{'id':'a1','journal':'A','date':'2026-11-05'},{'id':'a2','journal':'A','date':'2026-11-04'},{'id':'b1','journal':'B','date':'2026-11-03'}]
  self.assertEqual([r['id'] for r in translate_queue.ordered_groups(rows)],['a1','b1','a2'])
 def test_journals_finish_before_relevant_biorxiv_without_losing_rejected_rows(self):
  calls=[]
  class FakeTranslator:
   model='plamo-test'
   def __init__(self,*a):pass
   def connect(self):return self
   def translate(self,text):calls.append(text);return '訳:'+text
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);work=root/'work';work.mkdir();(root/'config').mkdir()
   write(root/'config/automation.json',{'base_url':'local','max_tokens':100})
   write(root/'config/sources.json',load(ROOT/'config/sources.json'))
   rows=[{'id':'bio','doi':'10.1234/bio','journal':'bioRxiv','preprint':True,'title':'Marine bacterial ecology','abstract':'Bio abstract','rights_status':'pending'},
         {'id':'journal','doi':'10.1234/journal','journal':'mBio','title':'Unusual pathway','abstract':'Journal abstract','rights_status':'allowed'},
         {'id':'excluded','doi':'10.1234/excluded','journal':'bioRxiv','preprint':True,'title':'Cancer in humans','abstract':'Tumour development','rights_status':'pending'}]
   write(work/'inbox.json',rows)
   with patch.object(translate_queue,'ROOT',root),patch.object(translate_queue,'Translator',FakeTranslator),patch.object(sys,'argv',['queue','--work-dir',str(work),'--include-pending','--batch-size','1']):
    self.assertEqual(translate_queue.main(),0)
   self.assertEqual(calls,['Unusual pathway','Journal abstract','Marine bacterial ecology','Bio abstract'])
   self.assertEqual(len(load(work/'inbox.json')),3)
   self.assertEqual(len(load(work/'translated.json')),2)
   self.assertEqual(load(work/'translation-status.json')['phase'],'complete')
if __name__=='__main__':unittest.main()
