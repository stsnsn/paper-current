"""Add configured journal profiles and synchronize the standalone demo scripts."""
import json,math
from common import ROOT,load

def main():
    path=ROOT/'docs/journal-options.js';source=path.read_text()
    start=source.index('const JOURNAL_PROFILES=')+len('const JOURNAL_PROFILES=');end=source.index(';\n',start)
    profiles=json.loads(source[start:end])
    for name,entry in load(ROOT/'config/sources.json')['source_journals'].items():
        profiles.setdefault(name,{'scope':entry['scope']})
    # Quiz weights are intentionally independent of the JIFs shown in the UI.
    metrics=load(ROOT/'config/quiz-journal-metrics.json')['journals']
    for entry in metrics:
        value=entry['value']
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
            raise ValueError('Invalid quiz IF: '+entry['name'])
        profile=profiles.setdefault(entry['name'],{'scope':entry.get('scope',[])})
        profile.update({'if':value,'year':entry['year'],'source':entry['source'],
            'if_kind':entry['kind'],'if_checked_on':entry['checked_on']})
        for field in ('proxy_for','note'):
            if field in entry:profile['if_'+field]=entry[field]
    missing=set(profiles)-{entry['name'] for entry in metrics}
    if missing:raise ValueError('Missing quiz IF: '+', '.join(sorted(missing)))
    source=source[:start]+json.dumps(profiles,ensure_ascii=False,indent=2)+source[end:]
    aliases=load(ROOT/'config/sources.json').get('journal_aliases',{})
    marker='const JOURNAL_ALIASES='
    if marker in source:
        a=source.index(marker)+len(marker);b=source.index(';\n',a);source=source[:a]+json.dumps(aliases,ensure_ascii=False)+source[b:]
    else:source=source.replace('function journalKey(name)',marker+json.dumps(aliases,ensure_ascii=False)+';\nfunction journalKey(name)')
    path.write_text(source)
    path=ROOT/'preview.html'
    if not path.exists():
        print('Journal profiles:',len(profiles))
        return
    preview=path.read_text()
    style_start=preview.index('<style>')+len('<style>');style_end=preview.index('</style>',style_start)
    preview=preview[:style_start]+(ROOT/'docs/style.css').read_text()+preview[style_end:]
    data_start=preview.index('window.PAPER_DATA = ');data_end=preview.index('</script>',data_start)
    preview=preview[:data_start]+(ROOT/'docs/data/papers.js').read_text().replace('</','<\\/')+preview[data_end:]
    start=preview.find('window.PAPER_JOURNALS = ')
    if start<0:start=preview.index("'use strict';")
    end=preview.index('</script>',start)
    scripts='\n'.join((ROOT/name).read_text() for name in ['docs/data/observed-journals.js','docs/journal-options.js','docs/data/journal-metrics.js','docs/app.js'])
    path.write_text(preview[:start]+scripts+'\n'+preview[end:])
    print('Journal profiles:',len(profiles))
if __name__=='__main__':main()
