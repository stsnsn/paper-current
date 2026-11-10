import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import cloud_daily as cloud
from common import write,load

class BackfillRequestTests(unittest.TestCase):
    def test_partial_then_complete_and_failure_never_blocks_normal_pipeline(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);work=root/'work/cloud'
            write(root/'config/backfill-request.json',{'id':'test','apply':True,'since':'2026-10-20','until':'2026-11-10'})
            original={'source_collected_at':{'bioRxiv':'old'}}
            write(work/'auto-state.json',original)
            with patch.object(cloud,'ROOT',root),patch('backfill.run_backfill',side_effect=RuntimeError('network failed')):
                self.assertFalse(cloud.process_backfill_request(work))
            state=load(work/'auto-state.json')
            self.assertEqual(state['backfill_request_status']['phase'],'retry')
            self.assertNotIn('completed_backfill_requests',state)
            report={'applied':True,'complete':False,'collection_exit_code':-9,'budget_exhausted':True,'additional':3,'coverage':{}}
            with patch.object(cloud,'ROOT',root),patch('backfill.run_backfill',return_value=report):
                self.assertFalse(cloud.process_backfill_request(work))
            self.assertEqual(load(work/'auto-state.json')['backfill_request_status']['phase'],'in_progress')
            report.update(complete=True,collection_exit_code=0,budget_exhausted=False)
            with patch.object(cloud,'ROOT',root),patch('backfill.run_backfill',return_value=report) as run:
                self.assertTrue(cloud.process_backfill_request(work))
                self.assertFalse(cloud.process_backfill_request(work))
                self.assertEqual(run.call_count,1)
            self.assertEqual(load(work/'auto-state.json')['source_collected_at'],original['source_collected_at'])
