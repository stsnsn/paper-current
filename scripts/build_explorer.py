"""Build year-sharded search data and document-level English term occurrences."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
from common import ROOT,dedupe_records,load,without_license_metadata

STOP=set('a an the and or but of in on at to for from by with without within between into through across than as is are was were be been being this that these those it its their our we they them which who also can could may might will would should have has had do does did not no more most less such both each other all any some using used use based study studies results result show showed shows found findings suggest suggests reveal revealed analysis analyses associated including different new novel significant significantly high higher low lower increase increased decreases decreased potential important role effects effect however therefore here thus well many during under over among against provide provides examined investigated respectively compared approach data method methods'.split())
GENERIC=set('bacteria bacterial archaea archaeal microbial microorganism microorganisms gene genes genome genomes genomic species samples sample sequence sequences community communities diversity function functions functional protein proteins cell cells environmental environment research'.split())
STOP.update('example examples freely abundant abundance predicted predictions obtained obtain propose proposed demonstrate demonstrated improve improved available previously previously observed observations particular specific consistent furthermore additional further together distinct major largely often common generally typically characterized identified identification understanding understand insight insights underlying basis utilized enabled enabling extensive several numerous novel crucial highly first second third ability able occur occurring present presence absence aim aims recent recently reveals reveals'.split())
PHRASES=['dissolved organic matter','dissolved organic carbon','organic carbon','carbon cycling','nitrogen cycling','sulfur cycling','oxygen minimum zone','single cell','single cell genomics','long read','long read sequencing','short read','metagenome assembled genomes','antibiotic resistance','antimicrobial resistance','horizontal gene transfer','gene transfer','gene expression','genome streamlining','comparative genomics','microbial carbon pump','carbon fixation','carbon metabolism','nitrogen fixation','amino acid','amino acids','fatty acids','climate change','global warming','deep sea','deep ocean','surface ocean','marine snow','cold water','hydrogen peroxide','reactive oxygen species','viral infection','host range','host virus','quorum sensing','type vi secretion','crisper cas','crispr cas','microbial dark matter','metabolic pathways','metabolic potential','transport systems','nutrient limitation','phosphorus limitation','iron limitation','ocean acidification','marine bacteria','marine archaea','marine viruses','microbial communities','microbial ecology','marine microbiome','ocean microbiome','coral reefs','bacterioplankton communities']
ALIASES={'sar11':'SAR11','sar86':'SAR86','dna':'DNA','rna':'RNA','rrna':'rRNA','crispr':'CRISPR','pelagibacter':'Pelagibacter','poseidoniales':'Poseidoniales','prochlorococcus':'Prochlorococcus','synechococcus':'Synechococcus','roseobacter':'Roseobacter','nitrosopumilus':'Nitrosopumilus'}


def clean(value):
    return re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',str(value or ''))).strip()


def tokens(row):
    return re.findall(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*',clean(row.get('title','')+' '+row.get('abstract','')).lower().replace('-',' '))


def extract_terms(rows):
    docs=[tokens(r) for r in rows];counts=Counter();pairs=Counter()
    for words in docs:
        counts.update(set(w for w in words if len(w)>=4 and w not in STOP and w not in GENERIC))
        pairs.update(set(' '.join(words[i:i+2]) for i in range(len(words)-1) if all(len(w)>=4 and w not in STOP for w in words[i:i+2]) and any(w not in GENERIC for w in words[i:i+2])))
    collocations={p for p,n in pairs.items() if n>=3 and n/max(1,min(counts[p.split()[0]],counts[p.split()[1]]))>=.3}
    phrases=set(PHRASES)|collocations
    output=[]
    for words in docs:
        body=' '+' '.join(words)+' '
        found={p for p in phrases if ' '+p+' ' in body}
        singles={w for w in words if len(w)>=4 and w not in STOP and w not in GENERIC}
        found={p for p in found if not any(p!=q and ' '+p+' ' in ' '+q+' ' for q in found)}
        singles-={w for p in found for w in p.split() if w not in ALIASES}
        terms=sorted(found,key=lambda p:(-len(p.split()),p))[:24]+sorted(singles,key=lambda w:(-math.log((1+len(rows))/(1+counts[w])),w))[:32]
        output.append(sorted({ALIASES.get(t,t) for t in terms}|{ALIASES[w] for w in words if w in ALIASES}))
    return output


def read_js(path):
    return json.loads(path.read_text().split('=',1)[1].strip().rstrip(';'))


def build(root=ROOT):
    base=Path(root)/'docs/data';index=load(base/'archive-index.json',{'issues':[]});rows=[];issues={}
    for entry in index['issues']:
        path=Path(root)/'docs'/entry['path']
        if not path.exists():raise FileNotFoundError('Archive required for full search: '+str(path))
        for row in load(path,{}).get('papers',[]):
            rows.append(row);issues[row['id']]=entry['id']
    for name in ('papers.js','recent-papers.js'):
        path=base/name
        if path.exists():
            value=read_js(path);rows.extend(value['papers'] if isinstance(value,dict) else value)
    rows=dedupe_records(rows);terms=extract_terms(rows);years={}
    fields=('id','doi','title','title_ja','abstract','abstract_ja','journal','date','preprint','review','collected_at','collected_date','collection_order','first_seen','source_url')
    for row,words in zip(rows,terms):
        paper={k:row[k] for k in fields if k in row};paper['terms']=words;paper['issue']=issues.get(row['id'],'')
        year=str(row.get('date',''))[:4];year=year if re.fullmatch(r'\d{4}',year) else 'unknown'
        years.setdefault(year,[]).append(without_license_metadata(paper))
    target=base/'explorer';target.mkdir(parents=True,exist_ok=True);entries=[]
    for year,papers in sorted(years.items(),reverse=True):
        raw=json.dumps(papers,ensure_ascii=False,separators=(',',':'))+'\n';digest=hashlib.sha256(raw.encode()).hexdigest()[:12];name=f'{year}-{digest}.json'
        (target/name).write_text(raw)
        entries.append({'year':year,'count':len(papers),'path':'data/explorer/'+name,'bytes':len(raw.encode())})
    manifest={'version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'count':len(rows),'years':entries,'journals':sorted({r.get('journal','') for r in rows if r.get('journal')}),'filter_years':sorted({str(r.get(field,''))[:4] for r in rows for field in ('date','collected_date','first_seen') if re.match(r'^\d{4}',str(r.get(field,'')))},reverse=True),'method':'English title + abstract; phrase/word extraction; binary document occurrence. No model inference.'}
    temporary=target/'index.tmp'
    temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(target/'index.json')
    active={Path(entry['path']).name for entry in entries}
    for old in target.glob('*.json'):
        if re.fullmatch(r'(?:\d{4}|unknown)-[a-f0-9]{12}\.json',old.name) and old.name not in active:
            old.unlink()
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args();result=build();print('Indexed',result['count'],'papers in',len(result['years']),'year shards')
