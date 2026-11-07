"""Europe PMC discovery uses both index arrival and recent publication dates."""
import datetime as dt


def publication_start(now,cfg):
    return (now-dt.timedelta(days=cfg.get('europepmc_publication_days',21))).date().isoformat()


def discovery_query(base,start,today,published_since,journals_only=False):
    return (base+' AND FIRST_IDATE:['+start+' TO '+today+']'
            +' AND FIRST_PDATE:['+published_since+' TO 3000-12-31]' 
            +(' NOT SRC:PPR' if journals_only else ''))


def recent_publication(record,start,today):
    try:
        date=dt.date.fromisoformat(record.get('firstPublicationDate',''))
        return dt.date.fromisoformat(start)<=date
    except (ValueError,TypeError):
        return False


def watchlist_query(cfg):
    return '('+' OR '.join('TITLE:"'+term+'" OR ABSTRACT:"'+term+'"'
                          for term in cfg.get('europepmc_watchlist',[]))+')'
