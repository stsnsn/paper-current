"""Summarize collected venues and generate the browser's observed journal catalog."""
import argparse,json
from pathlib import Path
from common import ROOT,load,write
from journal_catalog import update_catalog,summarize_journals

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',nargs='?',default=str(ROOT/'work/inbox.json'))
    p.add_argument('--output',default=str(ROOT/'docs/data/observed-journals.js'))
    p.add_argument('--report',default=str(ROOT/'work/journal-summary.json'))
    args=p.parse_args();rows=load(args.input,[]);cfg=load(ROOT/'config/sources.json')
    feeds=cfg.get('feed_journals',{});catalog_path=Path(args.input).parent/'journal-catalog.json'
    catalog=update_catalog(load(catalog_path,[]),rows,feeds);write(catalog_path,catalog)
    report=summarize_journals(rows,feeds);write(args.report,report)
    data={'summary':report,'journals':catalog}
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix('.tmp');tmp.write_text('window.PAPER_JOURNALS = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n',encoding='utf-8');tmp.replace(out)
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
