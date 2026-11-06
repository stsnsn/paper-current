const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('docs/app.js','utf8').split('(async()=>')[0];
function setup(data,storage=new Map()){
  const elements=new Map(),scrolls=[],app={innerHTML:'',querySelectorAll(){return []}};
  const document={documentElement:{},querySelector(selector){
    if(selector==='#app')return app;
    if(selector==='#archive-panel')return null;
    if(!elements.has(selector))elements.set(selector,{});
    return elements.get(selector);
  }};
  const math=Object.create(Math);math.random=()=>0;
  const ctx=vm.createContext({console,Math:math,document,window:{PAPER_DATA:data,scrollTo(...args){scrolls.push(args)}},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},location:{search:'',pathname:'/'},history:{replaceState(){}},URLSearchParams});
  vm.runInContext(fs.readFileSync('docs/journal-options.js','utf8'),ctx);vm.runInContext(fs.readFileSync('docs/data/journal-metrics.js','utf8'),ctx);vm.runInContext(source,ctx);
  return {run:code=>vm.runInContext(code,ctx),app,elements,scrolls,storage};
}
const data={issue:{id:'random-test',publication_mode:'daily'},papers:Array.from({length:12},(_,i)=>({id:'10.1234/'+i,doi:'10.1234/'+i,title:'Paper '+i,title_ja:'論文'+i,abstract:'Marine microbial ecology',abstract_ja:'海洋微生物のゲノム解析',journal:'mBio',date:'2026-11-'+String(i+1).padStart(2,'0')}))};
const original=JSON.stringify(data),test=setup(data),{run}=test;
run('resumeUnanswered()');
const order=run('JSON.stringify(state.paperOrder)'),firstBatch=run('JSON.stringify(getBatch().map(p=>p.id))');
assert.notEqual(order,JSON.stringify(data.papers.map(p=>p.id)));
assert.equal(run('new Set(state.paperOrder).size'),12);
// Reload and language changes cannot change the active round or its current paper.
run("state.answers[current().id]={first:'Nature'};persist()");
const firstId=run('current().id');
const reloaded=setup(data,test.storage);
assert.equal(reloaded.run('current().id'),firstId);
assert.equal(reloaded.run('JSON.stringify(getBatch().map(p=>p.id))'),firstBatch);
run("changePaperLanguage('en');goHome();resumeUnanswered()");
assert.equal(run('current().id'),firstId);assert.equal(run('JSON.stringify(state.paperOrder)'),order);
// Finishing every round (including a skip) must never present an answered paper.
const seen=new Set();
for(let i=0;i<12;i++){
  const id=run('current().id');assert(!seen.has(id));seen.add(id);
  assert(!run('isAnswered(current())'));
  if(i===0)run('skipPaper()'); // A first prediction prevents skipping; finish it below.
  if(i===1)run('skipPaper()');
  else run("state.answers[current().id]={first:'mBio',final:'mBio'};state.index++;normalize();persist()");
  if(run("state.screen==='summary'")&&!run('allComplete()'))run('resumeUnanswered()');
}
assert.equal(seen.size,12);assert(run('allComplete()'));
assert.equal(JSON.stringify(data),original);
// New daily additions preserve the whole saved order and all old answers.
run("papers.push({id:'new-a',title:'New A'},{id:'new-b',title:'New B'});resumeUnanswered()");
assert.equal(run('JSON.stringify(state.paperOrder.slice(0,12))'),order);
assert(['new-a','new-b'].includes(run('current().id')));
assert.equal(run('Object.keys(state.answers).length'),12);
assert.equal(run('orderedPapers().filter(p=>!isAnswered(p)).length'),2);
run("for(const p of papers)state.answers[p.id]={skipped:true};replay()");
assert.equal(run('state.paperOrder'),undefined);assert.equal(run('Object.keys(state.answers).length'),0);
assert.equal(run('state.history[0].lap'),1);
// A legacy round must migrate without changing its five papers or partial answer.
const legacy=setup(data);
legacy.run("state={batch:1,index:2,screen:'home',answers:{}};for(const p of papers.slice(0,7))state.answers[p.id]={final:'mBio'};state.answers[papers[7].id]={first:'Nature'};resumeUnanswered()");
assert.equal(legacy.run('current().id'),data.papers[7].id);
assert.equal(legacy.run('JSON.stringify(getBatch().map(p=>p.id))'),JSON.stringify(data.papers.slice(5,10).map(p=>p.id)));
assert.equal(legacy.run('state.answers[current().id].first'),'Nature');
console.log('Random rounds persist across reloads, preserve legacy progress, append new papers and never repeat answered papers.');

const browse=setup({issue:{id:'browse-test'},papers:[
  {id:'a',doi:'10.1234/a',title:'<i>Alpha</i> ocean',title_ja:'アオイ海',abstract:'Marine MICROBE',abstract_ja:'ゲノム解析',journal:'mBio',date:'2026-11-01'},
  {id:'b',doi:'10.1234/b',title:'Beta genome',title_ja:'ミドリの研究',abstract:'Freshwater',abstract_ja:'淡水微生物',journal:'Nature',date:'2026-11-06'},
  {id:'c',doi:'10.1234/c',title:'Gamma',title_ja:'シロイ研究',abstract:'Nothing related',abstract_ja:'別の研究',journal:'Science'}
]});
const br=browse.run;
br("changeContent('latest');latestQuery='ＭＡＲＩＮＥ ゲノム';paperLang='en'");
assert.equal(br('JSON.stringify(latestRows().map(p=>p.id))'),'["a"]');
br("paperLang='ja';latestQuery='alpha'");assert.equal(br('latestRows()[0].id'),'a');
br("paperLang='en';latestQuery='淡水'");assert.equal(br('latestRows()[0].id'),'b');
br("latestQuery='';latestSort='added'");assert.equal(br('JSON.stringify(latestRows().map(p=>p.id))'),'["c","b","a"]');
br("latestSort='date'");assert.equal(br('JSON.stringify(latestRows().map(p=>p.id))'),'["b","a","c"]');
br("latestSort='title'");assert.equal(br('JSON.stringify(latestRows().map(p=>p.id))'),'["a","b","c"]');
br("paperLang='ja'");assert.equal(br('JSON.stringify(latestRows().map(p=>p.id))'),'["a","c","b"]');
br('latestView()');
const markup=browse.app.innerHTML,scrollCount=browse.scrolls.length,search=browse.elements.get('#latest-search');
// Typing updates the result region instead of remounting the input or scrolling.
search.oninput({target:{value:'no match'}});
assert.equal(browse.app.innerHTML,markup);assert.equal(browse.elements.get('#latest-search'),search);
assert.equal(browse.scrolls.length,scrollCount);
assert(browse.elements.get('#latest-results').innerHTML.includes('一致する論文がありません'));
assert.equal(browse.elements.get('#latest-result-count').textContent,'0 / 3本');
search.oninput({target:{value:'Marine ゲノム'}});
assert(browse.elements.get('#latest-results').innerHTML.includes('アオイ海'));
assert(!browse.elements.get('#latest-results').innerHTML.includes('ミドリの研究'));
br("latestQuery='<img src=x onerror=alert(1)>';latestView()");
assert(!browse.app.innerHTML.includes('value="<img'));assert(browse.app.innerHTML.includes('&lt;img'));
console.log('Bilingual multi-term search, normalized text, stable sorting, missing dates, empty results and input stability passed.');

// IF sorting uses the same 2025 two-year JIF throughout; unknown is not zero.
const impacts=setup({issue:{id:'if-test'},papers:[
 {id:'unknown',journal:'Unverified journal',title:'Unknown'},
 {id:'bio',journal:'Nature',title:'Preprint',preprint:true},
 {id:'low',journal:'Microbiology (Reading, England)',title:'Low'},
 {id:'high',journal:'Nature Microbiology',title:'High'},
 {id:'middle',journal:'The ISME Journal',title:'Middle'},
 {id:'unknown-new',journal:'Unverified journal',title:'Unknown new'}
]});
const ir=impacts.run;
ir("changeContent('latest');latestSort='if'");
assert.equal(ir('JSON.stringify(latestRows().map(p=>p.id))'),'["high","middle","low","unknown-new","bio","unknown"]');
assert.equal(ir("paperImpact(papers[2]).value"),4.3);
assert.equal(ir("paperImpact(papers[0])"),null);assert.equal(ir("paperImpact(papers[1])"),null);
ir('latestView()');
assert(impacts.app.innerHTML.includes('IF順（2025）'));
assert(impacts.app.innerHTML.includes('2025 IF 18.7'));
assert(impacts.app.innerHTML.includes('https://www.nature.com/nmicrobiol/journal-impact'));
assert(!impacts.app.innerHTML.includes('2025 IF 0.0'));
assert(ir("paperImpactHTML(papers[1])===''") );
const metrics=ir('window.PAPER_JOURNAL_METRICS');
assert.equal(metrics.year,2025);assert.equal(metrics.release_year,2026);
assert.equal(new Set(metrics.journals.map(m=>m.name)).size,metrics.journals.length);
assert(metrics.journals.every(m=>Number.isFinite(m.value)&&m.value>0&&m.source.startsWith('https://')));
assert(metrics.unavailable.some(m=>m.name==='eLife'&&m.status==='not_assigned'));
console.log('2025 IF ranking, aliases, preprint exclusion, unknown values and source links passed.');
