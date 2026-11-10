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
PURPOSE = r'\b(?:estimat\w*|compar\w*|classif\w*|taxonom\w*|calculat\w*|comput\w*|infer\w*|assess\w*|evaluat\w*|tool\w*|method\w*|algorithm\w*|framework\w*|reconstruct\w*)\b'


def hits(terms, body):
    return [t for t in terms if re.search(r'\b'+re.escape(t)+r'\w*\b', body, re.I)]


def method_hits(title, abstract):
    # Title or a sentence stating a method/use; background-only mentions do not suffice.
    found=hits(SPECIFIC,title)
    for sentence in re.split(r'[.!?]\s+',abstract):
        if re.search(PURPOSE,sentence,re.I):found+=hits(SPECIFIC,sentence)
    return sorted(set(found))


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
    return scoped_query(cfg)+' OR '+field_query(SPECIFIC)
