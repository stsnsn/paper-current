const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map(),storage=new Map();
const app={innerHTML:'',querySelectorAll(){return []}};
const document={documentElement:{},querySelector(s){if(s==='#app')return app;if(s==='#archive-panel')return null;if(!elements.has(s))elements.set(s,{});return elements.get(s)}};
const data={issue:{id:'test'},papers:Array.from({length:7},(_,i)=>({id:'10.1234/'+i,doi:'10.1234/'+i,title:'Paper '+i,journal:'The ISME Journal',options:['The ISME Journal','Nature','Science','mBio']}))};
const ctx=vm.createContext({console,document,window:{PAPER_DATA:data,scrollTo(){}},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},location:{search:'',pathname:'/'},history:{replaceState(){}},URLSearchParams});
vm.runInContext(fs.readFileSync('docs/journal-options.js','utf8'),ctx);
let source=fs.readFileSync('docs/app.js','utf8');source=source.slice(0,source.lastIndexOf('(async()=>'));
vm.runInContext(source,ctx);
const run=code=>vm.runInContext(code,ctx);
for(const mode of ['beginner','professional'])for(const p of [...data.papers,{id:'forecast',preprint:true,tags:['海洋微生物']}]){
 ctx.paper=p;ctx.testMode=mode;
 const choices=run("journalOptions(paper,papers,testMode,'test')");assert.equal(choices.length,4);assert.equal(new Set(choices).size,4);assert(!choices.includes('bioRxiv'));if(!p.preprint)assert(choices.includes(p.journal));
 assert.deepEqual(choices,run("journalOptions(paper,papers,testMode,'test')"));
}
assert(run("journalDistance(journalProfile('The ISME Journal'),journalProfile('ISME Communications')) < journalDistance(journalProfile('The ISME Journal'),journalProfile('Science'))"));
assert(run("journalDistance({scope:['ecology'],if:10,year:2025},{scope:['ecology'],if:11,year:2025}) < journalDistance({scope:['ecology'],if:10,year:2025},{scope:['ecology'],if:30,year:2025})"));
run('home()');assert(app.innerHTML.includes('Beginner'));assert(app.innerHTML.includes('Professional'));assert(!app.innerHTML.includes('data-action="replay"'));
run("state.answers[papers[0].id]={first:'mBio',final:'mBio'};persist();changeMode('professional')");assert.equal(run('Object.keys(state.answers).length'),0);
run("changeMode('beginner')");assert.equal(run('Object.keys(state.answers).length'),1);
// Completing the first five of seven must not offer a second pass.
run("for(const p of papers.slice(0,5))state.answers[p.id]={first:p.journal,final:p.journal};state.index=5;summary()");assert(!app.innerHTML.includes('data-action="replay"'));assert(app.innerHTML.includes('残り2問'));
run("for(const p of papers)state.answers[p.id]={first:p.journal,final:p.journal};state.batch=1;state.index=2;summary()");assert(app.innerHTML.includes('2周目へ'));
run("saved.keep={id:'keep'};replay()");assert.equal(run('state.lap'),2);assert.equal(run('Object.keys(state.answers).length'),0);assert.equal(run('Object.keys(state.history[0].answers).length'),7);assert(run('Boolean(saved.keep)'));assert.equal(run('state.batch'),0);
run("state.screen='quiz';quiz()");assert(app.innerHTML.includes('2周目'));assert(app.innerHTML.includes('data-action="confirm"'));assert(!app.innerHTML.includes('result-banner'));
run("persist();switchIssue({issue:{id:'archive'},papers:INITIAL_DATA.papers},true);changeMode('professional');switchIssue(INITIAL_DATA,false);changeMode('beginner')");assert.equal(run('state.lap'),2);
console.log('Quiz modes, choice integrity, progress isolation, partial rounds and replay passed.');
// Catalog growth reaches choices, regenerates unstarted questions, and keeps
// an in-flight title/abstract pair stable across a catalog update.
run("state.answers={};state.optionSets={};state.optionVersions={};DATA.journal_catalog=[{name:'New Ecology Journal',scope:['microbiology','ecology']}]");
assert(run("Array.from({length:30},(_,i)=>journalOptions(papers[0],papers,'professional','seed'+i,DATA.journal_catalog)).some(options=>options.includes('New Ecology Journal'))"));
run("optionsFor(papers[0]);state.answers[papers[0].id]={first:state.optionSets[papers[0].id][0]};optionsFor(papers[1])");
const frozen=run('JSON.stringify(state.optionSets[papers[0].id])'),version=run('state.optionVersions[papers[1].id]');
run("DATA.journal_catalog.push({name:'Another New Journal',scope:['genomics']});optionsFor(papers[0]);optionsFor(papers[1])");
assert.equal(run('JSON.stringify(state.optionSets[papers[0].id])'),frozen);assert.notEqual(run('state.optionVersions[papers[1].id]'),version);
console.log('Catalog growth and in-flight option preservation passed.');
ctx.observed=[{name:'New RSS Venue',scope:['ecology']},{name:'bioRxiv',scope:[]}];
assert(run("observedJournalCatalog([{name:'New RSS Venue',scope:['genomics']}],observed).length===1"));
assert.equal(run("observedJournalCatalog([{name:'New RSS Venue',scope:['genomics']}],observed)[0].scope.length"),2);
run("window.PAPER_JOURNALS={journals:observed};viewingArchive=false;state.answers={};optionsFor(papers[2])");
assert(run("observedJournalCatalog([],window.PAPER_JOURNALS.journals).some(j=>j.name==='New RSS Venue')"));
assert(run('state.optionVersions[papers[2].id].length<=8'));
console.log('Observed collection catalog integration passed.');

// Reading and journal quiz are distinct pools and histories.
run("INITIAL_DATA.papers.push({id:'10.1234/bio',doi:'10.1234/bio',title:'Microbial evolution',abstract:'A full preprint abstract',title_ja:'微生物の進化',abstract_ja:'日本語要旨',preprint:true,journal:'bioRxiv'});changeContent('biorxiv');state.screen='quiz';quiz()");
assert.equal(run('papers.length'),1);assert(app.innerHTML.includes('A full preprint abstract'));assert(app.innerHTML.includes('日本語要旨'));assert(!app.innerHTML.includes('data-action="choice"'));assert(app.innerHTML.includes('掲載先を予測してみてください'));
run('advancePreprint()');assert(app.innerHTML.includes('1本読了'));assert(app.innerHTML.includes('2周目へ'));assert(!app.innerHTML.includes('scoregrid'));
run("changeContent('journals')");assert.equal(run('papers.length'),7);assert(!run('papers.some(p=>p.preprint)'));
run("changeContent('biorxiv')");assert(run('allComplete()'));
run('replay()');assert.equal(run('state.lap'),2);assert(!run('allComplete()'));
run("switchIssue({issue:{id:'empty-journals'},papers:[INITIAL_DATA.papers.at(-1)]},false);changeContent('journals');home()");assert(app.innerHTML.includes('まだありません'));assert(!app.innerHTML.includes('data-action="start"'));
console.log('Separate journal quiz and bioRxiv open reading modes passed.');

ctx.scrollCalls=[];run('window.scrollX=0;window.scrollY=640;window.scrollTo=(...position)=>scrollCalls.push(position)');
run("switchIssue(INITIAL_DATA,false);changeContent('journals');window.scrollY=640;changeMode('professional')");
assert.equal(ctx.scrollCalls.at(-1)[1],640);assert.equal(ctx.scrollCalls.at(-1)[0],0);
run('window.scrollY=880;changeMode("beginner")');assert.equal(ctx.scrollCalls.at(-1)[1],880);
run("state.screen='quiz';render()");assert.equal(ctx.scrollCalls.at(-1)[1],0);
console.log('Difficulty changes preserve scroll; page transitions still reset it.');

assert(run("journalKey('PNAS')===journalKey('Proceedings of the National Academy of Sciences of the United States of America')"));
assert(run("journalKey('Bioinformatics')===journalKey('Bioinformatics (Oxford, England)')"));
console.log('Publisher journal aliases resolve to the same choice.');

run("changeContent('journals');state.screen='quiz';state.batch=0;state.index=0;window.scrollY=1200;toggleSaved(current())");
assert.equal(ctx.scrollCalls.at(-1)[1],1200);assert(run('Boolean(saved[current().id])'));
run('window.scrollY=1250;toggleSaved(current())');assert.equal(ctx.scrollCalls.at(-1)[1],1250);assert(!run('Boolean(saved[current().id])'));
run("changeContent('biorxiv');state.screen='quiz';state.index=0;window.scrollY=1500;toggleSaved(current())");assert.equal(ctx.scrollCalls.at(-1)[1],1500);assert(app.innerHTML.includes('保存済み'));
console.log('Read-later toggles preserve scroll in both reading modes.');

ctx.csvRow={id:'paper',title:'A, "quoted" title\nnext line',title_ja:'日本語タイトル',journal:'mBio',doi:'10.1234/test'};
const csv=run('readingListCSV([csvRow])');assert(csv.startsWith('\uFEFF'));assert(csv.includes('"A, ""quoted"" title\nnext line"'));assert(csv.includes('日本語タイトル'));assert(csv.includes('https://doi.org/10.1234/test'));assert(csv.endsWith('\r\n'));
assert(run("readingListCSV([{title:'=HYPERLINK(1)',title_ja:'  +formula'}]).includes(\"'=HYPERLINK(1)\")"));
run('savedView()');assert(app.innerHTML.includes('data-action="export-csv"'));assert(app.innerHTML.includes('data-action="export"'));
console.log('CSV export includes BOM, Japanese, quoted multiline fields, links and formula-safe cells.');
let downloaded,createdBlob,revoked;
ctx.Blob=class{constructor(parts,options){createdBlob={parts,options}}};
ctx.URL={createObjectURL(){return 'blob:reading-list'},revokeObjectURL(url){revoked=url}};
ctx.setTimeout=fn=>fn();
document.createElement=()=>({click(){downloaded={href:this.href,name:this.download}}});
run("downloadReadingList('csv')");assert.equal(downloaded.name,'paper-current-reading-list.csv');assert.equal(createdBlob.options.type,'text/csv;charset=utf-8');assert(createdBlob.parts[0].startsWith('\uFEFF'));assert.equal(revoked,'blob:reading-list');
run("downloadReadingList('json')");assert.equal(downloaded.name,'paper-current-reading-list.json');assert.equal(createdBlob.options.type,'application/json');assert(Array.isArray(JSON.parse(createdBlob.parts[0])));
console.log('CSV and JSON download filenames, MIME types and blob cleanup passed.');
