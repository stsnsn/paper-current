"""Independent collection windows: a failed source never inherits another's cursor."""
import datetime as dt
import math

def source_start(state,source,now,default_days):
    last=state.get('source_collected_at',{}).get(source) or state.get('source_collection_baseline')
    days=default_days
    if last:
        days=max(3,math.ceil((now-dt.datetime.fromisoformat(last)).total_seconds()/86400)+2)
    return (now-dt.timedelta(days=days)).date().isoformat()

def advance_sources(state,coverage,now):
    cursors=state.setdefault('source_collected_at',{})
    for source,result in coverage.items():
        if result.get('ok'):cursors[source]=now.isoformat()
