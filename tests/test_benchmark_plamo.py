import sys,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from benchmark_plamo import translate_sample

class BenchmarkTests(unittest.TestCase):
    def test_four_papers_run_two_at_a_time_with_sequential_fields(self):
        barrier=threading.Barrier(2);lock=threading.Lock();active=[0];peak=[0];calls=[]
        class FakeTranslator:
            def __init__(self,*args):pass
            def translate(self,text):
                with lock:
                    active[0]+=1;peak[0]=max(peak[0],active[0]);calls.append(text)
                barrier.wait(timeout=3)
                with lock:active[0]-=1
                return '訳:'+text
        rows=[{'id':str(i),'title':f'title{i}','abstract':f'abstract{i}'} for i in range(4)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda row:translate_sample(row,'unused',FakeTranslator),rows))
        self.assertEqual(peak[0],2);self.assertEqual(len(results),4)
        for i,result in enumerate(results):
            self.assertTrue(result['success'])
            self.assertLess(calls.index(f'title{i}'),calls.index(f'abstract{i}'))
            self.assertEqual(result['fields']['abstract']['translation'],f'訳:abstract{i}')
            self.assertGreaterEqual(result['seconds'],0)

    def test_four_concurrent_papers(self):
        barrier=threading.Barrier(4)
        class FakeTranslator:
            def __init__(self,*args):pass
            def translate(self,text):
                barrier.wait(timeout=3)
                return '訳:'+text
        rows=[{'id':str(i),'title':'title','abstract':'abstract'} for i in range(4)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda row:translate_sample(row,'unused',FakeTranslator),rows))
        self.assertEqual(len(results),4)
        self.assertTrue(all(r['success'] for r in results))

    def test_failure_keeps_title_and_records_error(self):
        class FakeTranslator:
            def __init__(self,*args):pass
            def translate(self,text):
                if text=='abstract':raise RuntimeError('truncated')
                return '訳:'+text
        result=translate_sample({'id':'x','title':'title','abstract':'abstract'},'unused',FakeTranslator)
        self.assertFalse(result['success'])
        self.assertEqual(result['fields']['title']['translation'],'訳:title')
        self.assertEqual(result['fields']['abstract']['error'],'truncated')

if __name__=='__main__':unittest.main()
