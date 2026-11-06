"""Repair stored RSS abstracts and archive hashes without fetching or retranslating.

Run with --apply after reviewing the reported files. No paper-ID exceptions.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from common import ROOT,load,write
from rss_records import NATURE_RSS_JOURNALS,rss_abstract
from translate import fingerprint

def repair_record(row):
    if row.get('abstract_source')!='rss':return row
    result=copy.deepcopy(row)
    cache=result.get('translation',{}).get('abstract',{})
    valid_cache=bool(cache.get('model') and row.get('abstract_ja')
        and cache.get('hash')==fingerprint(row.get('abstract',''),cache['model']))
    abstract=rss_abstract(row.get('abstract',''),row.get('journal',''),row.get('doi',''))
    translated=row.get('abstract_ja','')
    if not abstract:
        translated=''
    elif row.get('journal') in NATURE_RSS_JOURNALS:
        identifier=row.get('doi','')
        index=translated.lower().find(identifier.lower()) if identifier else -1
        header=bool(re.match(r'^'+re.escape(row['journal'])+r'[,、]',translated))
        if header and index>=0:translated=translated[index+len(identifier):].strip()
        elif header:
            # A translated header without its DOI has no safe cut point.
            # Retry this abstract instead of stopping the entire state save.
            translated=''
    elif row.get('journal')=='PNAS':
        translated=re.sub(r'^Proceedings of the National Academy of Sciences, Volume \d+, Issue [^.]+\.\s*','',translated)
        translated=re.sub(r'^(?:Proceedings of the National Academy of Sciences|米国科学アカデミー紀要|米国科学アカデミー会報|PNAS)[,、誌\s]*','',translated)
        translated=re.sub(r'^第\d+巻\s*第\d+号[^。]*。\s*','',translated)
    if abstract==row.get('abstract','') and translated==row.get('abstract_ja',''):return row
    if not valid_cache:translated=''
    result['abstract']=abstract;result['abstract_ja']=translated
    if abstract and translated and valid_cache:
        cache['hash']=fingerprint(abstract,cache['model'])
        cache['postprocessing']='rss-publication-metadata-v1'
    else:result.get('translation',{}).pop('abstract',None)
    return result

def repair_data(value):
    if isinstance(value,list):return [repair_data(item) for item in value]
    if isinstance(value,dict):
        if 'abstract' in value:return repair_record(value)
        return {key:repair_data(item) for key,item in value.items()}
    return value

def migrate(root,work,apply=False):
    paths=sorted((root/'docs/data/issues').glob('*.json'))
    paths += [root/'docs/data/papers.js',root/'docs/data/recent-papers.js',work/'inbox.json',work/'translated.json']
    changed=[];issue_hashes={}
    for path in paths:
        if not path.exists():continue
        raw=path.read_text();prefix=''
        if path.suffix=='.js':prefix,raw=raw.split(' = ',1);raw=raw.strip().removesuffix(';')
        original=json.loads(raw);repaired=repair_data(original)
        if repaired==original:continue
        output=json.dumps(repaired,ensure_ascii=False,indent=2)
        if prefix:output=prefix+' = '+output+';\n'
        changed.append(str(path))
        if path.parent==root/'docs/data/issues':issue_hashes[path.stem]=hashlib.sha256(output.encode()).hexdigest()
        if apply:path.write_text(output,encoding='utf-8')
    index_path=root/'docs/data/archive-index.json';index=load(index_path)
    if issue_hashes and index:
        for issue in index['issues']:
            if issue['id'] in issue_hashes:issue['sha256']=issue_hashes[issue['id']]
        changed.append(str(index_path))
        if apply:write(index_path,index)
    return changed

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true');parser.add_argument('--work-dir',type=Path,default=ROOT/'work')
    args=parser.parse_args()
    for path in migrate(ROOT,args.work_dir,args.apply):print(path)
