import datetime as dt
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from epmc_search import discovery_query,recent_publication,publication_start,watchlist_query
from topic_filter import classify

class EuropePMCDiscovery(unittest.TestCase):
    def test_index_arrival_does_not_admit_old_or_unknown_publications(self):
        query=discovery_query('(marine bacteria)','2026-11-04','2026-11-07','2026-10-17')
        self.assertIn('FIRST_IDATE:[2026-11-04 TO 2026-11-07]',query)
        self.assertIn('FIRST_PDATE:[2026-10-17 TO 3000-12-31]',query)
        for date in ('2017-01-04','2026-10-16','','2026'):
            self.assertFalse(recent_publication({'firstPublicationDate':date},'2026-10-17','2026-11-07'))
        for date in ('2026-10-17','2026-11-07','2026-11-08','2027-01-01'):
            self.assertTrue(recent_publication({'firstPublicationDate':date},'2026-10-17','2026-11-07'))
        self.assertEqual(publication_start(dt.datetime(2026,11,7),{}),'2026-10-17')

    def test_watchlist_is_independent_of_journal_and_microbial_vocabulary(self):
        cfg={'europepmc_watchlist':['SAR11','Pelagibacter','Poseidoniales','SAR86'], 'excluded_journals':['Example']}
        query=watchlist_query(cfg)
        self.assertNotIn('JOURNAL:',query)
        for term in cfg['europepmc_watchlist']:
            self.assertIn('TITLE:"'+term+'"',query)
            self.assertIn('ABSTRACT:"'+term+'"',query)
            for field in ('title','abstract'):
                self.assertTrue(classify({field:term.lower(),'journal':'Other'},cfg)['accepted'])
        self.assertFalse(classify({'title':'SAR11','journal':'Example'},cfg)['accepted'])
        self.assertFalse(classify({'title':'SAR110','journal':'Other'},cfg)['accepted'])
