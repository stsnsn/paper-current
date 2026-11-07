"""Deterministic topic selection. No model, network, or title-similarity inference."""
import re
from common import normalized

def watchlist_hits(row,cfg):
    body=row.get('title','')+' '+row.get('abstract','')
    return [term for term in cfg.get('europepmc_watchlist',[])
            if re.search(r'\b'+re.escape(term)+r'\b',body,re.I)]



def canonical_journal(name,cfg):
    key=normalized(name).removeprefix('the')
    aliases={normalized(alias).removeprefix('the'):target for alias,target in cfg.get('journal_aliases',{}).items()}
    name=aliases.get(key,name);key=normalized(name).removeprefix('the')
    return next((candidate for candidate in cfg.get('source_journals',{}) if normalized(candidate).removeprefix('the')==key),name)

def journal_excluded(name,cfg):
    journal=canonical_journal(name,cfg)
    key=normalized(journal).removeprefix('the')
    allowed=cfg.get('frontiers_allowed_journals')
    if allowed is not None and (key.startswith('frontiers') or re.match(r'^front\.?\s',journal,re.I)):
        return key not in {normalized(canonical_journal(j,cfg)).removeprefix('the') for j in allowed}
    return bool(key) and any(normalized(canonical_journal(j,cfg)).removeprefix('the')==key for j in cfg.get('excluded_journals',[]))

def classify(row,cfg):
    rules=cfg.get('filtering',{});body=row.get('title','')+' '+row.get('abstract','')
    journal=canonical_journal(row.get('journal',''),cfg);sources=cfg.get('source_journals',{})
    watchlist=watchlist_hits(row,cfg)
    if watchlist:
        return {'accepted':True,'reason':'watchlist_keyword','version':rules.get('version','legacy'),'matched':watchlist,'context':{'marine':watchlist,'genomics':[],'evolution':[]},'tags':['海洋微生物']}
    if journal_excluded(journal,cfg):
        return {'accepted':False,'reason':'excluded_journal','version':rules.get('version','legacy'),'matched':[],'context':{'marine':[],'genomics':[],'evolution':[]},'tags':[]}
    profile=next((v for name,v in sources.items() if normalized(name).removeprefix('the')==normalized(journal).removeprefix('the')), {})
    matches=[]
    for pattern in rules.get('microbial_patterns',[]):
        matches.extend(m.group(0).lower() for m in re.finditer(pattern,body,re.I))
    for taxon in rules.get('microbial_taxa',[]):
        if re.search(r'\b'+re.escape(taxon)+r'\b',body,re.I):matches.append(taxon)
    def hits(terms):
        return [term for term in terms if re.search(r'\b'+re.escape(term)+(r'\b' if len(term)<=3 else r'\w*'),body,re.I)]
    marine=hits(rules.get('marine_terms',cfg.get('marine_terms',[])))
    genome=hits(rules.get('genomics_terms',cfg.get('genomics_method_terms',[])))
    evolution=hits(rules.get('evolution_terms',[]))
    unfiltered=not row.get('preprint') and profile.get('filter')=='none'
    # Old configurations retain their existing broad vocabulary behaviour.
    if not rules:matches=matches or hits(cfg.get('genomics_organism_terms',[]))
    marine_preprint=bool(row.get('preprint') and marine)
    accepted=unfiltered or bool(matches) or marine_preprint
    tags=[]
    if marine:tags.append('海洋微生物')
    if genome:tags.append('微生物ゲノミクス')
    if evolution:tags.append('微生物進化')
    if not tags:tags=['微生物学']
    return {'accepted':accepted,'reason':'unfiltered_journal' if unfiltered else 'microbial_evidence' if matches else 'marine_preprint' if marine_preprint else 'no_microbial_evidence',
            'version':rules.get('version','legacy'),'matched':sorted(set(matches)),
            'context':{'marine':marine,'genomics':genome,'evolution':evolution},'tags':tags}

def annotate(row,cfg):
    row=dict(row)
    if row.get('id') in cfg.get('archive_only_ids',[]):row['archive_only']=True
    if not row.get('journal'):
        names={cfg.get('feed_journals',{}).get(source) for source in row.get('sources',[])}-{None,''}
        if len(names)==1:row['journal']=names.pop()
    if row.get('journal'):row['journal']=canonical_journal(row['journal'],cfg)
    decision=classify(row,cfg)
    return {**row,'topic_filter':decision,'tags':decision['tags']}
