import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from backfill import candidates

class BackfillTests(unittest.TestCase):
    def test_doi_aliases_archive_and_missing_metadata(self):
        rows=[{'id':d,'doi':d,'journal':'Specialist','title':'Test','abstract':'Full'} for d in ['10.1234/a','10.1234/b','10.1234/c','10.1234/d']]
        rows[-1]['abstract']=''
        inbox=[dict(rows[1],doi='https://doi.org/10.1234/B')]
        index={'issues':[{'doi_keys':['10.1234/a']}]}
        added,report=candidates(rows+rows,inbox,index,{'source_journals':{'Specialist':{'filter':'none'}}})
        self.assertEqual([r['doi'] for r in added],['10.1234/c','10.1234/d'])
        self.assertEqual([r['status'] for r in report],['published','queued','translation_pending','metadata_pending'])

    def test_request_applies_only_after_success_without_advancing_cursor(self):
        import tempfile,json
        from unittest.mock import patch
        import backfill
        from common import write,load
        from types import SimpleNamespace
        for code in (0,2):
            with self.subTest(code=code),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);work=root/'work';out=root/'out'
                write(root/'config/sources.json',{'source_journals':{'Specialist':{'filter':'none'}}})
                write(root/'docs/data/archive-index.json',{'issues':[{'doi_keys':['10.1234/issued']}]})
                write(work/'inbox.json',[]);write(work/'auto-state.json',{'source_collected_at':{'bioRxiv':'2026-11-01'}})
                request=root/'request.json';write(request,{'since':'2026-10-20','until':'2026-11-10','routes':'biorxiv','apply':True})
                def collect(cmd):
                    write(out/'candidates.json',[{'id':d,'doi':d,'journal':'Specialist','title':'Test','abstract':'Full'} for d in ('10.1234/issued','10.1234/new')])
                    return SimpleNamespace(returncode=code)
                argv=['backfill','--request',str(request),'--work-dir',str(work),'--output-dir',str(out)]
                with patch.object(backfill,'ROOT',root),patch.object(sys,'argv',argv),patch.object(backfill.subprocess,'run',side_effect=collect):
                    if code:
                        with self.assertRaises(SystemExit):backfill.main()
                    else:backfill.main()
                self.assertEqual(load(work/'auto-state.json'),{'source_collected_at':{'bioRxiv':'2026-11-01'}})
                self.assertEqual([r['doi'] for r in load(work/'inbox.json')],['10.1234/new'] if code==0 else [])
                self.assertEqual(load(out/'backfill-report.json')['applied'],code==0)
