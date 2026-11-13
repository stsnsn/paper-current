"""arXiv candidate discovery; all results still require local topic evidence."""
import re
from common import text


def arxiv_query(since, until):
    def terms(values):
        return '('+' OR '.join('(ti:"'+v+'" OR abs:"'+v+'")' for v in dict.fromkeys(values))+')'
    # Broad candidate retrieval stays compact enough for the API URL limit.
    # Local filtering uses the complete vocabulary, including methods/resources.
    topic='cat:q-bio.* OR '+terms(['microbial','bacterial','archaeal','metagenomic','microbiome','phage','bioinformatics','protein','genome','genomic','sequence','sequencing','phylogenetic','transcriptomic','RNA','DNA'])
    return '('+topic+') AND lastUpdatedDate:['+since.replace('-','')+'0000 TO '+until.replace('-','')+'2359]'


def arxiv_record(entry, query):
    match=re.fullmatch(r'https?://arxiv.org/abs/(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v(\d+))?',entry.get('id',''))
    if not match:raise ValueError('Invalid arXiv entry identifier')
    identifier=match[1];d='10.48550/arxiv.'+identifier.lower()
    return dict(id=d,doi=d,arxiv_id=identifier,version=match[2] or '1',
                title=text(entry.get('title','')),abstract=text(entry.get('summary','')),
                journal='arXiv',preprint=True,date=entry.get('published','')[:10],
                authors=', '.join(a.get('name','') for a in entry.get('authors',[])),
                source_url='https://arxiv.org/abs/'+identifier,abstract_source='arXiv',
                discovery=[{'source':'arXiv','query':query,'scope':'candidate'}])
