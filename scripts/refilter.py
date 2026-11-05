"""Re-evaluate saved records using deterministic source/topic rules, retaining every row."""
import argparse
from collections import Counter
from common import ROOT,load,write
from topic_filter import annotate

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out');p.add_argument('--report');args=p.parse_args()
    cfg=load(ROOT/'config/sources.json');rows=[annotate(row,cfg) for row in load(args.input,[])]
    report={'total':len(rows),'accepted':sum(row['topic_filter']['accepted'] for row in rows),
            'reasons':dict(Counter(row['topic_filter']['reason'] for row in rows))}
    write(args.out or args.input,rows)
    if args.report:write(args.report,report)
    print(report)
if __name__=='__main__':main()
