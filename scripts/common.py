import json,os,re,tempfile,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p,default=None):
    p=Path(p)
    return json.loads(p.read_text()) if p.exists() else default

def write(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=p.parent,delete=False,encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);name=f.name
    os.replace(name,p)
def text(s):return html.unescape(re.sub('<[^>]*>','',s or '')).strip()
def normalized(s):return re.sub('[^a-z0-9]','',s.lower())

# DOI variants are identifiers, never separate papers.
from urllib.parse import unquote

def doi(value):
    value=unquote(html.unescape(str(value or ''))).strip()
    match=re.search(r'10\.\d{4,9}/[^\s<>"?#]+',value,re.I)
    if not match:return ''
    value=match.group().rstrip('.,;').lower()
    if value.startswith(('10.1101/','10.64898/')):
        value=re.sub(r'(?:v\d+)?(?:\.full(?:\.pdf)?|\.abstract)?/?$','',value)
    return value

def paper_keys(row):
    values=[row.get(k,'') for k in ('doi','id','published_doi','preprint_doi')]+row.get('related_dois',[])
    keys={doi(v) for v in values if doi(v)}
    return keys or {str(row.get('id',''))}

def dedupe_records(rows):
    """Merge exact DOI aliases, including explicitly linked preprint/publication.
    Never infer a relationship solely from similar titles, or copy a license
    from one textual version to another.
    """
    parent={}
    def find(k):
        parent.setdefault(k,k)
        if parent[k]!=k:parent[k]=find(parent[k])
        return parent[k]
    for row in rows:
        keys=sorted(paper_keys(row));head=find(keys[0])
        for k in keys[1:]:parent[find(k)]=find(head)
    groups={}
    for row in rows:groups.setdefault(find(next(iter(paper_keys(row)))),[]).append(row)
    result=[]
    for group in groups.values():
        def rank(pair):
            index,r=pair
            try:version=int(r.get('version',0))
            except (ValueError,TypeError):version=0
            return (bool(r.get('abstract') and r.get('rights_status')=='allowed'),bool(r.get('abstract')),not r.get('preprint',False),version,index)
        best=dict(max(enumerate(group),key=rank)[1])
        aliases=sorted({k for r in group for k in paper_keys(r) if doi(k)})
        best['doi']=doi(best.get('doi',''))
        pre=[k for k in aliases if k.startswith(('10.1101/','10.64898/'))]
        best['id']=pre[0] if pre else (best['doi'] or best.get('id'))
        best['related_dois']=aliases
        best['sources']=sorted({s for r in group for s in r.get('sources',[])})
        best['tags']=sorted({s for r in group for s in r.get('tags',[])})
        dates=[r['first_seen'] for r in group if r.get('first_seen')]
        if dates:best['first_seen']=min(dates)
        for r in group:
            if r.get('published_doi'):best['published_doi']=doi(r['published_doi'])
            if r.get('published_journal'):best['published_journal']=r['published_journal']
        result.append(best)
    return result
