import sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from process_control import run_bounded

class BoundedProcessTests(unittest.TestCase):
    def test_timeout_stops_grandchild_writer(self):
        with tempfile.TemporaryDirectory() as temp:
            marker=Path(temp)/'late-write'
            child="import time,pathlib;time.sleep(.5);pathlib.Path("+repr(str(marker))+").write_text('orphan')"
            parent="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);time.sleep(30)"
            code,timed_out=run_bounded([sys.executable,'-c',parent],.15)
            self.assertTrue(timed_out);self.assertNotEqual(code,0)
            time.sleep(.6)
            self.assertFalse(marker.exists())
