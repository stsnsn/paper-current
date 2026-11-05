"""Build a static issue without any LLM. Deterministic distractors and order."""
import argparse,datetime as dt,hashlib,json,random
from pathlib import Path
from common import ROOT,load,write,dedupe_records
from journal_catalog import update_catalog,journal_key as normalized
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--id',default=dt.date.today().isoformat());p.add_argument('--label',default='今週の新着');p.add_argument('--journal-catalog');p.add_argument('--demo',action='store_true');p.add_argument('--out',default='docs/data/papers.js');args=p.parse_args()
cfg=load(ROOT/'config/sources.json');rows=dedupe_records(load(args.input,[]));seen=set();papers=[]
catalog=update_catalog(load(args.journal_catalog or Path(args.input).parent/'journal-catalog.json',[]),rows,cfg.get('feed_journals',{}))
journals={normalized(j):j for j in cfg['journals']}
for j in catalog:journals.setdefault(normalized(j['name']),j['name'])
for a in rows:
    if a.get('journal') and not a.get('preprint'):journals.setdefault(normalized(a['journal']),a['journal'])
    if a.get('published_journal'):journals.setdefault(normalized(a['published_journal']),a['published_journal'])
for a in rows:
    if not a.get('abstract') or not a.get('doi') or (not a.get('journal') and not a.get('preprint')):continue
    if not args.demo and (a.get('rights_status')!='allowed' or not a.get('title_ja') or not a.get('abstract_ja')):continue
    if a['id'] in seen:continue
    seen.add(a['id']);a=dict(a)
    answer=a.get('published_journal') if a.get('preprint') else a.get('journal')
    a['answer_journal']=journals.get(normalized(answer),answer) if answer else None
    a['question_type']='forecast' if not a['answer_journal'] else 'published'
    if not a.get('preprint'):a['journal']=a['answer_journal']
    # Same fixed distractor universe; no ranking by impact factor.
    rng=random.Random(hashlib.sha256((args.id+a['id']).encode()).hexdigest());pool=[j for k,j in journals.items() if k!=normalized(a['answer_journal'] or '')]
    if len(pool)<(3 if a['answer_journal'] else 4):raise ValueError('Need at least four distinct journals')
    a['options']=rng.sample(pool,3)+[a['answer_journal']] if a['answer_journal'] else rng.sample(pool,4)
    rng.shuffle(a['options']);papers.append(a)
if not papers:raise SystemExit('No eligible translated papers; existing issue was not modified.')
random.Random(args.id).shuffle(papers)
# Alternate thematic groups where possible. All eligible papers remain available.
marine=[a for a in papers if '海洋微生物' in a.get('tags',[])];other=[a for a in papers if a not in marine];ordered=[]
while marine or other:
    if marine:ordered.append(marine.pop())
    if other:ordered.append(other.pop())
issue={'issue':{'id':args.id,'label':args.label,'note':'試作版：実在するCC BY論文を使った体験用セットです。今週の新着の網羅的な選定ではありません。訳文は試作用で、PLaMo出力ではありません。' if args.demo else '新着候補から作成したクイズです。日本語はPLaMoによる機械翻訳です。'},'papers':ordered,'journal_catalog':catalog}
out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.tmp');tmp.write_text('window.PAPER_DATA = '+json.dumps(issue,ensure_ascii=False,indent=2)+';\n',encoding='utf-8');tmp.replace(out)
print('Built',len(ordered),'questions:',out)
