"""RSS metadata parsing, without fabricating abstract text."""
import calendar,datetime as dt,hashlib,re
from html.parser import HTMLParser
from common import without_license_metadata,text,doi
from topic_filter import annotate

NATURE_RSS_JOURNALS={
    'Nature','Nature Biotechnology','Nature Communications','Nature Ecology & Evolution',
    'Nature Microbiology','Nature Reviews Microbiology','Communications Biology',
    'npj Biofilms and Microbiomes',
}
METADATA_ONLY_JOURNALS={'Science','Science Advances','Molecular Phylogenetics and Evolution'}

class _RSSBlocks(HTMLParser):
    """Preserve HTML boundaries before removing publication metadata."""
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('p','div','br'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('p','div'):self.parts.append('\n')
    def handle_data(self,data):self.parts.append(data)

def rss_abstract(raw,journal,identifier=''):
    if journal not in NATURE_RSS_JOURNALS|METADATA_ONLY_JOURNALS|{'PNAS'}:
        return text(raw)
    parser=_RSSBlocks();parser.feed(raw or '')
    blocks=[s.strip() for s in ''.join(parser.parts).splitlines() if s.strip()]
    if journal in NATURE_RSS_JOURNALS:
        # Nature puts its journal/date/DOI in a separate paragraph. Do not
        # guess where a DOI ends after HTML boundaries have been discarded.
        cleaned=[]
        for block in blocks:
            if re.match(r'^'+re.escape(journal)+r',\s*Published online:',block):
                # Older saved records have lost their HTML paragraph boundaries.
                # Only the exact record DOI safely separates header and body.
                index=block.lower().find(identifier.lower()) if identifier else -1
                block=block[index+len(identifier):].strip() if index>=0 else ''
            cleaned.append(block)
        blocks=cleaned
    elif journal=='PNAS':
        blocks=[re.sub(r'^Proceedings of the National Academy of Sciences, Volume \d+, Issue [^.]+\.\s*','',s) for s in blocks]
    else:
        blocks=[s for s in blocks if not re.match(r'^(?:Publication date:|Source:|Author\(s\):|'+re.escape(journal)+r',\s*Volume\s+\d)',s)]
    return '\n\n'.join(s for s in blocks if s)

def normalize_rss_record(row):
    """Normalize at the persistence boundary, including previously saved RSS rows."""
    row=without_license_metadata(row)
    if row.get('abstract_source')!='rss':return dict(row)
    result=dict(row)
    result['abstract']=rss_abstract(row.get('abstract',''),row.get('journal',''),row.get('doi',''))
    if result['abstract']!=row.get('abstract',''):
        # A translation of the old input must not be published for the new input.
        for field in ('abstract_ja','translation','translation_label'):
            result.pop(field,None)
    return result

def rss_record(entry,url,cfg):
    title=text(entry.get('title',''));journal=cfg.get('feed_journals',{}).get(url,'')
    # Some feeds contain navigation/teasers, not abstracts; retain source provenance.
    if not title:return None
    d=next((doi(v) for v in [entry.get('prism_doi',''),entry.get('dc_identifier',''),entry.get('link',''),entry.get('id','')] if doi(v)), '')
    abstract=rss_abstract('\n'.join(c.get('value','') for c in entry.get('content',[])) or entry.get('summary',''),journal,d)
    key=d or 'rss:'+hashlib.sha256((title+entry.get('link','')).encode()).hexdigest()[:20]
    raw_date=entry.get('published_parsed') or entry.get('updated_parsed')
    date=dt.datetime.fromtimestamp(calendar.timegm(raw_date),dt.timezone.utc).date().isoformat() if raw_date else ''
    row=dict(id=key,title=title,abstract=abstract,journal=journal,doi=d,date=date,authors=text(entry.get('author','')),tags=[],
        source_url=entry.get('link',''),abstract_source='rss',preprint='biorxiv' in url)
    return annotate(row,cfg)

def merge_record(before,row,source):
    before=normalize_rss_record(before)
    row=normalize_rss_record(row)
    # RSS cannot overwrite richer API metadata or erase already saved abstracts.
    if before:
        for field in ('abstract','journal','doi','date','authors','source_url','abstract_source'):
            if not row.get(field) and before.get(field):row[field]=before[field]
        if row.get('abstract_source')=='rss' and before.get('abstract') and before.get('abstract_source')!='rss':
            row['abstract']=before['abstract'];row['abstract_source']=before.get('abstract_source','metadata')
        for field in ('title','abstract'):
            if before.get(field)==row.get(field) and before.get(field+'_ja'):row[field+'_ja']=before[field+'_ja']
        if before.get('title')==row.get('title') and before.get('abstract')==row.get('abstract'):
            for field in ('translation','translation_label'):
                if before.get(field):row[field]=before[field]
    result={**before,**row,'sources':sorted(set(before.get('sources',[])+[source])),
            'first_seen':before.get('first_seen',dt.date.today().isoformat())}
    for field in ('title','abstract'):
        if before.get(field)!=row.get(field) and field+'_ja' not in row:
            result.pop(field+'_ja',None)
            result.pop('translation',None);result.pop('translation_label',None)
    return normalize_rss_record(result)
