"""Recover missing Europe PMC metadata from the matching primary article's JATS XML."""
import copy,datetime as dt,re,xml.etree.ElementTree as ET
from pathlib import Path
from common import doi,load,write
BASE='https://www.ebi.ac.uk/europepmc/webservices/rest'

def local_name(node):return node.tag.rsplit('}',1)[-1]
def clean_text(node):return re.sub(r'\s+',' ',' '.join(node.itertext())).strip()

def parse_fulltext_metadata(xml):
    root=ET.fromstring(xml)
    meta=next((node for node in root.iter() if local_name(node)=='article-meta'),None)
    if meta is None:raise ValueError('No primary article metadata in XML')
    result={}
    for node in meta:
        if local_name(node)=='article-id':
            kind=node.get('pub-id-type','');value=clean_text(node)
            if kind=='doi':result['doi']=doi(value)
            elif kind in ('pmcid','pmid'):result[kind]=value
    for node in meta:
        if local_name(node)!='abstract':continue
        lang=node.get('{http://www.w3.org/XML/1998/namespace}lang','en').lower()
        kind=node.get('abstract-type','').lower()
        if not lang.startswith('en') or kind in ('graphical','toc','teaser','plain-language-summary','author-summary'):continue
        abstract=copy.deepcopy(node)
        for parent in list(abstract.iter()):
            for child in list(parent):
                name=local_name(child);title=next((clean_text(n).lower() for n in child if local_name(n)=='title'),'')
                if name in ('kwd-group','supplementary-material','ref-list') or child.get('sec-type') in ('kwd-group','supplementary-material') or (name=='sec' and title.startswith(('supplementary information','supplementary material','keywords','subject terms'))) or (name=='title' and clean_text(child).lower() in ('abstract','summary')):
                    parent.remove(child)
        value=clean_text(abstract)
        if value:result['abstractText']=value;break
    dates=[]
    for node in meta:
        if local_name(node)!='pub-date':continue
        parts={local_name(child):clean_text(child) for child in node}
        try:
            date=dt.date(int(parts['year']),int(parts['month']),int(parts['day'])).isoformat()
        except (ValueError,KeyError):continue
        electronic=node.get('pub-type') in ('epub','epub-ppub') or node.get('publication-format')=='electronic'
        dates.append((0 if electronic else 1,date))
    if dates:result['firstPublicationDate']=sorted(dates)[0][1]
    # Store explicit Creative Commons URLs only; non-BY conditions stay distinct.
    for node in meta.iter():
        if local_name(node)!='license':continue
        value=ET.tostring(node,encoding='unicode')
        match=re.search(r'https?://creativecommons\.org/licenses/(by(?:-[a-z]+)*)/(\d[\d.]*)/?',value,re.I)
        if match:result['license']='cc '+match.group(1).lower().replace('-',' ');break
    return result

def enrich_core(record,fetch,cache_dir):
    row=dict(record);pmcid=row.get('pmcid') or (row.get('id') if row.get('source')=='PMC' else None)
    if (row.get('abstractText') and row.get('doi')) or not re.fullmatch(r'PMC\d+',str(pmcid or '')):return row
    cache=Path(cache_dir)/(pmcid+'.json');metadata=load(cache)
    if metadata is None:
        response=fetch(f'{BASE}/{pmcid}/fullTextXML');response.raise_for_status()
        metadata=parse_fulltext_metadata(response.content)
        if metadata.get('pmcid') and metadata['pmcid']!=pmcid:raise ValueError('PMC identity differs from requested article')
        write(cache,metadata)
    if row.get('doi') and metadata.get('doi') and doi(row['doi'])!=metadata['doi']:raise ValueError('DOI differs between core metadata and XML')
    if row.get('pmid') and metadata.get('pmid') and str(row['pmid'])!=metadata['pmid']:raise ValueError('PMID differs between core metadata and XML')
    row['pmcid']=pmcid
    for field in ('doi','pmid','license'):
        if not row.get(field) and metadata.get(field):row[field]=metadata[field]
    if not row.get('abstractText') and metadata.get('abstractText'):
        row['abstractText']=metadata['abstractText'];row['abstract_source']='Europe PMC fullTextXML'
    if row.get('source')=='PMC' and metadata.get('firstPublicationDate'):row['firstPublicationDate']=metadata['firstPublicationDate']
    row['metadata_source_url']=f'{BASE}/{pmcid}/fullTextXML'
    return row
