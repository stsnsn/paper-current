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
