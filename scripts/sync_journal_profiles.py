"""Add configured journal profiles and synchronize the standalone demo scripts."""
import json
from common import ROOT,load

def main():
    path=ROOT/'docs/journal-options.js';source=path.read_text()
    start=source.index('const JOURNAL_PROFILES=')+len('const JOURNAL_PROFILES=');end=source.index(';\n',start)
    profiles=json.loads(source[start:end])
    for name,entry in load(ROOT/'config/sources.json')['source_journals'].items():
        profiles.setdefault(name,{'scope':entry['scope']})
    source=source[:start]+json.dumps(profiles,ensure_ascii=False,indent=2)+source[end:];path.write_text(source)
    path=ROOT/'preview.html';preview=path.read_text();start=preview.find('window.PAPER_JOURNALS = ')
    if start<0:start=preview.index("'use strict';")
    end=preview.index('</script>',start)
    scripts='\n'.join((ROOT/name).read_text() for name in ['docs/data/observed-journals.js','docs/journal-options.js','docs/app.js'])
    path.write_text(preview[:start]+scripts+'\n'+preview[end:])
    print('Journal profiles:',len(profiles))
if __name__=='__main__':main()
