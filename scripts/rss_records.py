"""RSS metadata parsing, without fabricating abstract text or reuse rights."""
import calendar,datetime as dt,hashlib,re
from common import text,doi
from topic_filter import annotate

def rss_record(entry,url,cfg):
    title=text(entry.get('title',''));journal=cfg.get('feed_journals',{}).get(url,'')
    abstract=text(' '.join(c.get('value','') for c in entry.get('content',[])) or entry.get('summary',''))
    # Some feeds contain navigation/teasers, not abstracts; retain source provenance.
    if not title:return None
    d=next((doi(v) for v in [entry.get('prism_doi',''),entry.get('dc_identifier',''),entry.get('link',''),entry.get('id','')] if doi(v)), '')
    key=d or 'rss:'+hashlib.sha256((title+entry.get('link','')).encode()).hexdigest()[:20]
    raw_date=entry.get('published_parsed') or entry.get('updated_parsed')
    date=dt.datetime.fromtimestamp(calendar.timegm(raw_date),dt.timezone.utc).date().isoformat() if raw_date else ''
    license_text=' '.join(str(entry.get(k,'')) for k in ('rights','dc_rights','creativeCommons_license','cc_license'))
    ccby=bool(re.search(r'creativecommons\.org/licenses/by/(?:\d|$)',license_text,re.I))
    row=dict(id=key,title=title,abstract=abstract,journal=journal,doi=d,date=date,authors=text(entry.get('author','')),tags=[],
        license='CC BY' if ccby else '',license_url=re.search(r'https?://creativecommons\.org/licenses/by/[^\s<>\"\x27]+',license_text).group(0) if ccby else '',
        source_url=entry.get('link',''),rights_status='allowed' if ccby else 'pending',abstract_source='rss',preprint='biorxiv' in url)
    return annotate(row,cfg)

def merge_record(before,row,source):
    # RSS cannot overwrite richer API metadata or erase already saved abstracts.
    if before:
        for field in ('abstract','journal','doi','date','authors','license','license_url','source_url','abstract_source'):
            if not row.get(field) and before.get(field):row[field]=before[field]
        if row.get('abstract_source')=='rss' and before.get('abstract') and before.get('abstract_source')!='rss':
            row['abstract']=before['abstract'];row['abstract_source']=before.get('abstract_source','metadata')
        if row.get('rights_status')=='pending' and before.get('rights_status')=='allowed' and source.startswith('http'):
            row['rights_status']='allowed';row['license']=before.get('license','');row['license_url']=before.get('license_url','')
        for field in ('title','abstract'):
            if before.get(field)==row.get(field) and before.get(field+'_ja'):row[field+'_ja']=before[field+'_ja']
        if before.get('title')==row.get('title') and before.get('abstract')==row.get('abstract'):
            for field in ('translation','translation_label'):
                if before.get(field):row[field]=before[field]
    return {**before,**row,'sources':sorted(set(before.get('sources',[])+[source])),
            'first_seen':before.get('first_seen',dt.date.today().isoformat())}
