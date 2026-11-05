'use strict';
// Scope tags are editorial groupings for this quiz, not journal rankings.
// IF entries are year-specific publisher snapshots. Missing IF stays unknown.
const JOURNAL_PROFILES={
  "Nature": {
    "scope": [
      "general"
    ]
  },
  "Science": {
    "scope": [
      "general"
    ]
  },
  "Nature Communications": {
    "scope": [
      "general",
      "biology"
    ],
    "if": 18.1,
    "year": 2025,
    "source": "https://www.nature.com/ncomms/"
  },
  "Nature Microbiology": {
    "scope": [
      "microbiology",
      "ecology"
    ],
    "if": 18.7,
    "year": 2025,
    "source": "https://www.nature.com/nmicrobiol/journal-impact"
  },
  "The ISME Journal": {
    "scope": [
      "microbiology",
      "ecology"
    ],
    "if": 10.2,
    "year": 2025,
    "source": "https://academic.oup.com/ismej/pages/about"
  },
  "ISME Communications": {
    "scope": [
      "microbiology",
      "ecology"
    ],
    "if": 6.4,
    "year": 2025,
    "source": "https://academic.oup.com/ismecommun/pages/about"
  },
  "mBio": {
    "scope": [
      "microbiology",
      "biology"
    ]
  },
  "mSystems": {
    "scope": [
      "microbiology",
      "genomics",
      "ecology"
    ]
  },
  "Applied and Environmental Microbiology": {
    "scope": [
      "microbiology",
      "ecology",
      "applied"
    ]
  },
  "Environmental Microbiology": {
    "scope": [
      "microbiology",
      "ecology"
    ]
  },
  "Microbiome": {
    "scope": [
      "microbiology",
      "ecology",
      "genomics"
    ]
  },
  "Genome Biology": {
    "scope": [
      "genomics",
      "biology"
    ]
  },
  "Genome Research": {
    "scope": [
      "genomics",
      "biology"
    ]
  },
  "Nucleic Acids Research": {
    "scope": [
      "genomics",
      "molecular"
    ]
  },
  "PLOS Genetics": {
    "scope": [
      "genomics",
      "biology"
    ]
  },
  "PLOS Biology": {
    "scope": [
      "biology",
      "general"
    ]
  },
  "Microbial Genomics": {
    "scope": [
      "microbiology",
      "genomics"
    ]
  },
  "Science Advances": {
    "scope": [
      "general",
      "biology"
    ]
  },
  "ISME Host Microbe": {
    "scope": [
      "microbiology",
      "ecology",
      "host"
    ]
  },
  "FEMS Microbiology Ecology": {
    "scope": [
      "microbiology",
      "ecology"
    ]
  },
  "FEMS Microbiology Letters": {
    "scope": [
      "microbiology"
    ]
  },
  "FEMS Microbiology Reviews": {
    "scope": [
      "microbiology"
    ]
  },
  "FEMS Yeast Research": {
    "scope": [
      "microbiology",
      "fungi"
    ]
  },
  "FEMS Microbes": {
    "scope": [
      "microbiology"
    ]
  },
  "microLife": {
    "scope": [
      "microbiology"
    ]
  },
  "NAR Genomics and Bioinformatics": {
    "scope": [
      "genomics",
      "methods"
    ]
  },
  "Bioinformatics": {
    "scope": [
      "genomics",
      "methods"
    ]
  },
  "Microbes and Environments": {
    "scope": [
      "microbiology",
      "ecology"
    ]
  },
  "Frontiers in Microbiology": {
    "scope": [
      "microbiology"
    ]
  },
  "Frontiers in Marine Science": {
    "scope": [
      "ecology",
      "marine"
    ]
  },
  "Microbiology Spectrum": {
    "scope": [
      "microbiology"
    ]
  },
  "mSphere": {
    "scope": [
      "microbiology"
    ]
  },
  "Journal of Bacteriology": {
    "scope": [
      "microbiology",
      "molecular"
    ]
  },
  "Journal of Virology": {
    "scope": [
      "microbiology",
      "virology"
    ]
  },
  "Microbiology and Molecular Biology Reviews": {
    "scope": [
      "microbiology",
      "molecular"
    ]
  },
  "Clinical Microbiology Reviews": {
    "scope": [
      "microbiology",
      "host"
    ]
  },
  "Infection and Immunity": {
    "scope": [
      "microbiology",
      "host"
    ]
  },
  "Antimicrobial Agents and Chemotherapy": {
    "scope": [
      "microbiology",
      "applied"
    ]
  },
  "Journal of Clinical Microbiology": {
    "scope": [
      "microbiology",
      "host"
    ]
  },
  "Microbiology Resource Announcements": {
    "scope": [
      "microbiology",
      "genomics"
    ]
  },
  "Nature Ecology & Evolution": {
    "scope": [
      "ecology",
      "evolution"
    ]
  },
  "Cell": {
    "scope": [
      "biology",
      "general"
    ]
  },
  "Cell Host & Microbe": {
    "scope": [
      "microbiology",
      "host"
    ]
  },
  "Environmental Microbiome": {
    "scope": [
      "microbiology",
      "ecology"
    ]
  },
  "Animal Microbiome": {
    "scope": [
      "microbiology",
      "host"
    ]
  },
  "Microbiology": {
    "scope": [
      "microbiology"
    ]
  },
  "Aquatic Microbial Ecology": {
    "scope": [
      "microbiology",
      "ecology",
      "marine"
    ]
  },
  "PNAS": {
    "scope": [
      "general",
      "biology"
    ]
  },
  "Microbial Ecology": {
    "scope": [
      "microbiology",
      "ecology"
    ]
  },
  "Environmental Microbiology Reports": {
    "scope": [
      "microbiology",
      "ecology"
    ]
  },
  "International Journal of Systematic and Evolutionary Microbiology": {
    "scope": [
      "microbiology",
      "evolution",
      "genomics"
    ]
  },
  "npj Biofilms and Microbiomes": {
    "scope": [
      "microbiology",
      "ecology",
      "host"
    ]
  },
  "Nature Reviews Microbiology": {
    "scope": [
      "microbiology"
    ]
  },
  "Trends in Microbiology": {
    "scope": [
      "microbiology"
    ]
  },
  "Annual Review of Microbiology": {
    "scope": [
      "microbiology"
    ]
  },
  "Microbial Cell": {
    "scope": [
      "microbiology",
      "molecular"
    ]
  },
  "Microbial Biotechnology": {
    "scope": [
      "microbiology",
      "applied"
    ]
  },
  "Extremophiles": {
    "scope": [
      "microbiology",
      "ecology"
    ]
  },
  "Genome Biology and Evolution": {
    "scope": [
      "genomics",
      "evolution"
    ]
  },
  "Molecular Biology and Evolution": {
    "scope": [
      "genomics",
      "evolution"
    ]
  },
  "Molecular Ecology": {
    "scope": [
      "ecology",
      "evolution"
    ]
  },
  "Molecular Ecology Resources": {
    "scope": [
      "ecology",
      "genomics",
      "methods"
    ]
  },
  "Molecular Phylogenetics and Evolution": {
    "scope": [
      "evolution",
      "genomics"
    ]
  },
  "Bioinformatics Advances": {
    "scope": [
      "genomics",
      "methods"
    ]
  },
  "Briefings in Bioinformatics": {
    "scope": [
      "genomics",
      "methods"
    ]
  },
  "Briefings in Functional Genomics": {
    "scope": [
      "genomics",
      "methods"
    ]
  },
  "BMC Genomics": {
    "scope": [
      "genomics"
    ]
  },
  "BMC Bioinformatics": {
    "scope": [
      "genomics",
      "methods"
    ]
  },
  "GigaScience": {
    "scope": [
      "genomics",
      "methods"
    ]
  },
  "Database": {
    "scope": [
      "genomics",
      "methods"
    ]
  },
  "DNA Research": {
    "scope": [
      "genomics"
    ]
  },
  "PLOS Computational Biology": {
    "scope": [
      "biology",
      "methods"
    ]
  },
  "Scientific Data": {
    "scope": [
      "general",
      "methods"
    ]
  },
  "Limnology and Oceanography": {
    "scope": [
      "marine",
      "ecology"
    ]
  },
  "Limnology and Oceanography Letters": {
    "scope": [
      "marine",
      "ecology"
    ]
  },
  "Annual Review of Marine Science": {
    "scope": [
      "marine",
      "ecology"
    ]
  },
  "Trends in Ecology & Evolution": {
    "scope": [
      "ecology",
      "evolution"
    ]
  },
  "iScience": {
    "scope": [
      "general",
      "biology"
    ]
  },
  "Current Biology": {
    "scope": [
      "biology",
      "general"
    ]
  },
  "Cell Reports": {
    "scope": [
      "biology",
      "general"
    ]
  },
  "Cell Reports Methods": {
    "scope": [
      "biology",
      "methods"
    ]
  },
  "Communications Biology": {
    "scope": [
      "biology",
      "general"
    ]
  },
  "Communications Earth & Environment": {
    "scope": [
      "ecology",
      "marine"
    ]
  },
  "Scientific Reports": {
    "scope": [
      "general"
    ]
  },
  "eLife": {
    "scope": [
      "biology",
      "general"
    ]
  },
  "PNAS Nexus": {
    "scope": [
      "general",
      "biology"
    ]
  },
  "BMC Biology": {
    "scope": [
      "biology",
      "general"
    ]
  },
  "PLOS ONE": {
    "scope": [
      "general"
    ]
  },
  "PeerJ": {
    "scope": [
      "biology",
      "general"
    ]
  },
  "Nature Methods": {
    "scope": [
      "biology",
      "methods"
    ]
  },
  "Nature Biotechnology": {
    "scope": [
      "biology",
      "applied"
    ]
  }
};
// Merge collection-derived profiles with the current issue, including future venues.
// Publisher-verified scope/IF in JOURNAL_PROFILES continues to take precedence.
function observedJournalCatalog(issueCatalog=[],observedCatalog=[]){
  const merged=new Map();
  for(const entry of [...observedCatalog,...issueCatalog]){
    if(!entry.name||journalKey(entry.name)==='biorxiv')continue;
    const key=journalKey(entry.name),old=merged.get(key);
    merged.set(key,{...old,...entry,scope:[...new Set([...(old?.scope||[]),...(entry.scope||[])])]});
  }
  return [...merged.values()].sort((a,b)=>journalKey(a.name).localeCompare(journalKey(b.name)));
}
const JOURNAL_ALIASES={"Proceedings of the National Academy of Sciences of the United States of America": "PNAS", "Current biology : CB": "Current Biology", "Microbiology (Reading, England)": "Microbiology", "Science (New York, N.Y.)": "Science", "Microbiology and molecular biology reviews : MMBR": "Microbiology and Molecular Biology Reviews", "Bioinformatics (Oxford, England)": "Bioinformatics", "Extremophiles : life under extreme conditions": "Extremophiles"};
function journalKey(name){const normalize=value=>String(value||'').toLowerCase().replace(/[^a-z0-9]/g,'').replace(/^the/,'');const key=normalize(name),alias=Object.entries(JOURNAL_ALIASES).find(([value])=>normalize(value)===key)?.[1];return alias?normalize(alias):key}
function journalProfile(name,catalog=[]){const k=journalKey(name);return Object.entries(JOURNAL_PROFILES).find(([j])=>journalKey(j)===k)?.[1]||catalog.find(j=>journalKey(j.name)===k)||{scope:[]}}
function optionRandom(seed){let n=2166136261;for(const c of seed)n=Math.imul(n^c.charCodeAt(0),16777619);return ()=>{n+=0x6D2B79F5;let x=Math.imul(n^(n>>>15),1|n);x^=x+Math.imul(x^(x>>>7),61|x);return ((x^(x>>>14))>>>0)/4294967296}}
function optionShuffle(rows,rng){const out=[...rows];for(let i=out.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[out[i],out[j]]=[out[j],out[i]]}return out}
function journalDistance(a,b){const shared=a.scope.filter(s=>b.scope.includes(s)).length,union=new Set([...a.scope,...b.scope]).size;let d=union?1-shared/union:1;if(a.if>0&&b.if>0&&a.year===b.year)d+=Math.min(1,Math.abs(Math.log(a.if/b.if)))*0.35;return d}
function journalOptions(p,papers,mode,seed,catalog=[]){
  const correct=p.answer_journal??(p.preprint?null:p.journal),rng=optionRandom(seed+':'+p.id+':'+mode),names=new Map();
  for(const name of [correct,...catalog.map(j=>j.name),...Object.keys(JOURNAL_PROFILES),...papers.flatMap(a=>[a.answer_journal,...(a.options||[])])])if(name&&journalKey(name)!=='biorxiv'&&!names.has(journalKey(name)))names.set(journalKey(name),name);
  let pool=optionShuffle([...names.values()].filter(j=>journalKey(j)!==journalKey(correct)),rng);
  if(mode==='professional'){
    // For unpublished preprints use topic tags rather than a fabricated answer.
    const topic={scope:(p.tags||[]).includes('海洋微生物')?['microbiology','ecology']:['microbiology','genomics']};
    const known=correct?journalProfile(correct,catalog):topic,target=known.scope.length?known:topic;
    pool.sort((a,b)=>journalDistance(target,journalProfile(a,catalog))-journalDistance(target,journalProfile(b,catalog)));
    // Sample from five near neighbours to avoid making every question identical.
    pool=optionShuffle(pool.slice(0,Math.max(correct?3:4,5)),rng);
  }
  const choices=pool.slice(0,correct?3:4);if(correct)choices.push(correct);
  return optionShuffle(choices,rng);
}

function optionFingerprint(value){let hash=2166136261;for(const c of value)hash=Math.imul(hash^c.charCodeAt(0),16777619);return (hash>>>0).toString(16)}
