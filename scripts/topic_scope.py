"""Shared, inspectable discovery vocabulary; no tool names or DOI allowlist."""
import re

MICROBIAL = ['microbial', 'microbe', 'microorganism', 'bacteria', 'bacterial', 'archaea', 'archaeal',
             'prokaryotic', 'prokaryote', 'fungal', 'fungi', 'yeast', 'protist', 'microalgae',
             'microalgal', 'virus', 'viral', 'virome', 'microbiome', 'microbiota', 'microbiology', 'microbiological', 'bacterium', 'archaeon', 'bacterioplankton', 'metagenom', 'metatranscriptom', 'methanotroph', 'methanogen', 'phage', 'bacteriophage', 'diatom', 'dinoflagellate', 'cyanobacteria']
AQUATIC = ['marine', 'ocean', 'aquatic', 'freshwater', 'seawater', 'estuarine', 'lake', 'river', 'plankton']
GENOMICS = ['genome', 'genomic', 'metagenome', 'metagenomic', 'pangenome', 'pangenomic',
            'phylogenomic', 'assembly', 'assemblies', 'binning', 'annotation', 'phylogenetic', 'phylogeny']
# The biological use of these phrases is explicit without an organism name.
SPECIFIC = ['average nucleotide identity', 'average amino acid identity', 'metagenome assembly',
            'metagenomic assembly', 'metagenome binning', 'metagenomic binning',
            'metagenome assembled genome', 'metagenome-assembled genome', '16S rRNA', '18S rRNA']
# General bioinformatics contributions, including reusable tools and databases.
BIO_DATA = ['sequence', 'sequencing', 'genome', 'genomic', 'metagenome', 'metagenomic',
            'pangenome', 'pangenomic', 'transcriptome', 'transcriptomic', 'proteome',
            'proteomic', 'protein', 'nucleotide', 'amino acid', 'DNA', 'RNA',
            'phylogenetic', 'phylogeny', 'bioinformatics', 'biological data', 'gene', 'genetic',
            'metabolome', 'metabolomic', 'epigenome', 'epigenomic', 'chromatin',
            'metabolic pathway', 'molecular interaction', 'biological network']
BIO_METHODS = ['algorithm', 'software', 'tool', 'method', 'framework', 'workflow',
               'pipeline', 'database', 'data base', 'knowledgebase', 'knowledge base',
               'web server', 'webserver', 'resource', 'benchmark', 'assembly',
               'assembler', 'alignment', 'aligner', 'annotation', 'binning',
               'clustering', 'classification', 'error correction', 'batch correction',
               'quality assessment', 'quality control', 'functional prediction', 'prediction',
               'predictor', 'simulation', 'inference', 'normalization', 'imputation',
               'visualization', 'dimensionality reduction']
CONTRIBUTION = r'\b(?:we\s+(?:present|introduc\w*|develop\w*|propos\w*|provid\w*|releas\w*|creat\w*|design\w*|implement\w*|build|built)|here\s+we\s+(?:present|introduc\w*|develop\w*|propos\w*|provid\w*)|(?:new|novel|updated|improved)\s+(?:\w+\s+){0,3}(?:algorithm|software|tool|method|framework|workflow|pipeline|database|resource|web\s+server))\b'


PURPOSE = r'\b(?:estimat\w*|compar\w*|classif\w*|taxonom\w*|calculat\w*|comput\w*|infer\w*|assess\w*|evaluat\w*|tool\w*|method\w*|algorithm\w*|framework\w*|reconstruct\w*)\b'


def hits(terms, body):
    return [t for t in terms if re.search(r'\b'+re.escape(t)+r'\w*\b', body, re.I)]


def method_hits(title, abstract):
    # Title or a sentence stating a method/use; background-only mentions do not suffice.
    found=hits(SPECIFIC,title)
    for sentence in re.split(r'[.!?]\s+',abstract):
        if re.search(PURPOSE,sentence,re.I):found+=hits(SPECIFIC,sentence)
    return sorted(set(found))


def bioinformatics_hits(title, abstract):
    found=[]
    # A methods/resource title is direct evidence of the paper's purpose.
    if hits(BIO_DATA,title) and hits(BIO_METHODS,title):
        found+=hits(BIO_DATA,title)+hits(BIO_METHODS,title)
    # Abstract-only mentions need an explicit contribution in the same sentence.
    for sentence in re.split(r'[.!?]\s+',abstract):
        if re.search(CONTRIBUTION,sentence,re.I) and hits(BIO_DATA,sentence) and hits(BIO_METHODS,sentence):
            found+=hits(BIO_DATA,sentence)+hits(BIO_METHODS,sentence)
    return sorted(set(found))


def bioinformatics_query():
    return '('+field_query(BIO_DATA)+' AND '+field_query(BIO_METHODS)+')'


def field_query(terms):
    return '('+' OR '.join('TITLE_ABS:"'+t+'"' if ' ' in t or '-' in t else 'TITLE_ABS:'+t+'*' for t in dict.fromkeys(terms))+')'


def scoped_query(cfg):
    taxa=cfg.get('filtering',{}).get('microbial_taxa',[])
    # Purpose terms are deliberately checked after retrieval for this broad candidate arm.
    # Thus it is not marked as an already scoped query.
    rules=cfg.get('filtering',{})
    context=AQUATIC+GENOMICS+rules.get('marine_terms',[])+rules.get('genomics_terms',[])
    return '('+field_query(MICROBIAL+taxa)+' AND '+field_query(context)+')'


def topic_query(cfg):
    return scoped_query(cfg)+' OR '+field_query(SPECIFIC)+' OR '+bioinformatics_query()
