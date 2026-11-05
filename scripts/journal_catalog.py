"""Accumulate observed venues independently of translation/publication eligibility."""
from common import normalized

def journal_key(name):return normalized(name).removeprefix('the')

def update_catalog(catalog, rows, feed_journals=None):
    by_key={journal_key(j['name']):{**j,'scope':list(j.get('scope',[]))} for j in catalog if j.get('name')}
    for row in rows:
        names=[row.get('published_journal')]
        if not row.get('preprint'):
            names.append(row.get('journal'))
            if not row.get('journal'):names.extend((feed_journals or {}).get(source) for source in row.get('sources',[]))
        scope=set()
        if '海洋微生物' in row.get('tags',[]):scope.update(('microbiology','ecology'))
        if '微生物ゲノミクス' in row.get('tags',[]):scope.update(('microbiology','genomics'))
        for name in names:
            if not name or normalized(name)=='biorxiv':continue
            key=journal_key(name);entry=by_key.setdefault(key,{'name':name,'scope':[]})
            entry['scope']=sorted(set(entry['scope'])|scope)
    return sorted(by_key.values(),key=lambda j:journal_key(j['name']))

def summarize_journals(rows, feed_journals=None):
    """Count observed venues, keeping preprint servers separate from journals."""
    from collections import Counter
    journals=Counter();servers=Counter();published=Counter();unknown=0
    catalog=update_catalog([],rows,feed_journals)
    canonical={journal_key(j['name']):j['name'] for j in catalog}
    for row in rows:
        if row.get('preprint'):
            servers[row.get('journal') or 'Unknown preprint server']+=1
        else:
            names=[row['journal']] if row.get('journal') else sorted(set(
                (feed_journals or {})[s] for s in row.get('sources',[]) if s in (feed_journals or {})))
            keys={journal_key(name) for name in names}
            if len(keys)==1:journals[canonical[next(iter(keys))]]+=1
            else:unknown+=1
        if row.get('published_journal'):published[canonical[journal_key(row['published_journal'])]]+=1
    counts=lambda c:[{'name':name,'count':count} for name,count in sorted(c.items(),key=lambda item:(-item[1],journal_key(item[0])))]
    return {'total':len(rows),'journals':counts(journals),'preprint_servers':counts(servers),
            'unknown_venue':unknown,'confirmed_publication_journals':counts(published),
            'missing_abstract':sum(not row.get('abstract') for row in rows)}
