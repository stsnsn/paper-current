import hashlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import cloud_daily as cloud
from common import write,load

class BackfillDurableStateTests(unittest.TestCase):
    def test_legacy_restore_then_resume_and_verify_checkpoint_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'repo/state';work=root/'work'
            for name in cloud.FILES:write(source/name,[] if name in ('inbox.json','translated.json','journal-catalog.json') else {})
            manifest={'schema_version':1,'sha256':{name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in cloud.FILES}}
            write(source/'manifest.json',manifest)
            cloud.restore_state(work,root/'repo')
            self.assertEqual(load(work/'backfill-progress.json'),{})
            progress={'sources':{'bioRxiv':{'cursor':100}},'records':[{'id':'10.1234/new'}]}
            write(source/'backfill-progress.json',progress)
            manifest['sha256']['backfill-progress.json']=hashlib.sha256((source/'backfill-progress.json').read_bytes()).hexdigest()
            write(source/'manifest.json',manifest)
            cloud.restore_state(work,root/'repo')
            self.assertEqual(load(work/'backfill-progress.json'),progress)
            write(source/'backfill-progress.json',{})
            with self.assertRaisesRegex(RuntimeError,'hash mismatch'):cloud.restore_state(work,root/'repo')
