import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import cloud_daily as cloud
from common import write,load

class BackfillRequestTests(unittest.TestCase):
    def test_success_recorded_once_and_failure_remains_pending(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);work=root/'work/cloud'
            write(root/'config/backfill-request.json',{'id':'test','apply':True})
            original={'source_collected_at':{'bioRxiv':'old'}}
            write(work/'auto-state.json',original)
            with patch.object(cloud,'ROOT',root),patch.object(cloud.subprocess,'run',side_effect=subprocess.CalledProcessError(2,['backfill'])):
                with self.assertRaises(subprocess.CalledProcessError):cloud.process_backfill_request(work)
            self.assertEqual(load(work/'auto-state.json'),original)
            write(work.parent/'backfill/backfill-report.json',{'collection_exit_code':0,'applied':True})
            with patch.object(cloud,'ROOT',root),patch.object(cloud.subprocess,'run') as run:
                self.assertTrue(cloud.process_backfill_request(work))
                self.assertFalse(cloud.process_backfill_request(work))
                self.assertEqual(run.call_count,1)
            self.assertEqual(load(work/'auto-state.json')['source_collected_at'],original['source_collected_at'])
