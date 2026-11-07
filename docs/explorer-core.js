(function(root){
'use strict';
const normalize=s=>String(s||'').replace(/<[^>]*>/g,' ').normalize('NFKC').toLowerCase().replace(/\s+/g,' ').trim();
const terms=p=>new Set(p.terms||[]);
function filter(papers,f={}){
 const words=normalize(f.query).split(/\s+/).filter(Boolean);
 return papers.filter(p=>{
  const date=String(p[f.dateField==='collected'?'collected_date':'date']|| (f.dateField==='collected'?(p.collected_at||p.first_seen):'')||'').slice(0,10);
  if(f.year&&date.slice(0,4)!==f.year)return false;
  if(f.start&&(!date||date<f.start)||f.end&&(!date||date>f.end))return false;
  if(f.kind==='journal'&&p.preprint||f.kind==='preprint'&&!p.preprint||f.kind==='review'&&!p.review)return false;
  if(f.journal&&p.journal!==f.journal)return false;
  const body=normalize([p.title,p.abstract,p.title_ja,p.abstract_ja,p.doi].join(' '));
  return words.every(w=>body.includes(w));
 });
}
function statistics(papers,limit=24){
 const counts=new Map();
 for(const p of papers)for(const term of terms(p))counts.set(term,(counts.get(term)||0)+1);
 const ranked=[...counts].map(([term,count])=>({term,count,share:papers.length?count/papers.length:0})).sort((a,b)=>b.count-a.count||a.term.localeCompare(b.term));
 const nodes=ranked.slice(0,limit),allowed=new Set(nodes.map(n=>n.term)),pairs=new Map();
 for(const p of papers){const list=[...terms(p)].filter(t=>allowed.has(t)).sort();for(let i=0;i<list.length;i++)for(let j=i+1;j<list.length;j++){const key=JSON.stringify([list[i],list[j]]);pairs.set(key,(pairs.get(key)||0)+1)}}
 const edges=[...pairs].map(([key,count])=>{const [a,b]=JSON.parse(key);return {a,b,count,strength:count/Math.sqrt(counts.get(a)*counts.get(b))}}).sort((a,b)=>b.strength-a.strength||b.count-a.count).slice(0,Math.max(65,limit*4));
 return {ranked,nodes,edges,total:papers.length};
}
function timeline(papers,selected,today){
 const buckets=new Map(),future=[],unknown=[];
 for(const p of papers){const date=String(p.date||'');if(!/^\d{4}-\d{2}-\d{2}$/.test(date)){unknown.push(p);continue}if(date>today){future.push(p);continue}const month=date.slice(0,7);if(!buckets.has(month))buckets.set(month,[]);buckets.get(month).push(p)}
 const keys=[...buckets.keys()].sort(),months=[];
 if(keys.length){let [year,month]=keys[0].split('-').map(Number);const end=keys[keys.length-1];while(`${year}-${String(month).padStart(2,'0')}`<=end&&months.length<2400){const key=`${year}-${String(month).padStart(2,'0')}`,rows=buckets.get(key)||[];months.push({month:key,total:rows.length,values:selected.map(term=>{const count=rows.filter(p=>terms(p).has(term)).length;return {term,count,share:rows.length?count/rows.length:0}})});if(++month>12){year++;month=1}}}
 return {months,future,unknown};
}
const api={normalize,filter,statistics,timeline};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PaperExplorer=api;
})(typeof window==='undefined'?globalThis:window);
