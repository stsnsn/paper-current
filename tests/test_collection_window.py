import datetime as dt
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collection_window import source_start,advance_sources

class CollectionWindows(unittest.TestCase):
    def test_failed_source_keeps_its_window_while_other_sources_advance(self):
        now=dt.datetime(2026,11,7,tzinfo=dt.timezone.utc)
        old=now-dt.timedelta(days=120)
        state={'source_collection_baseline':old.isoformat()}
        advance_sources(state,{'healthy':{'ok':True},'failed':{'ok':False}},now)
        tomorrow=now+dt.timedelta(days=1)
        self.assertEqual(source_start(state,'healthy',tomorrow,7),(tomorrow-dt.timedelta(days=3)).date().isoformat())
        self.assertEqual(source_start(state,'failed',tomorrow,7),(old-dt.timedelta(days=2)).date().isoformat())
        advance_sources(state,{'failed':{'ok':True}},tomorrow)
        self.assertEqual(state['source_collected_at']['failed'],tomorrow.isoformat())

    def test_initial_window_uses_configured_days(self):
        now=dt.datetime(2026,11,7,tzinfo=dt.timezone.utc)
        self.assertEqual(source_start({},'new',now,14),'2026-10-24')
