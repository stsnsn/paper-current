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
assert.equal(run('papers.length'),1);assert(!app.innerHTML.includes('A full preprint abstract'));assert(app.innerHTML.includes('日本語要旨'));
run("changePaperLanguage('en')");assert(app.innerHTML.includes('A full preprint abstract'));assert(!app.innerHTML.includes('日本語要旨'));
run("changePaperLanguage('ja')");assert(!app.innerHTML.includes('data-action="choice"'));assert(app.innerHTML.includes('掲載先を予測してみてください'));
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

// Single-language title/abstract rendering and title-stage-only skips.
run("switchIssue(INITIAL_DATA,false);changeContent('journals');state={batch:0,index:0,screen:'quiz',answers:{}};papers[0].title='Unique English title';papers[0].title_ja='固有の日本語題名';papers[0].abstract='Unique English abstract';papers[0].abstract_ja='固有の日本語要旨';paperLang='ja';render()");
assert(app.innerHTML.includes('固有の日本語題名'));assert(!app.innerHTML.includes('Unique English title'));assert(!app.innerHTML.includes('固有の日本語要旨'));assert(app.innerHTML.includes('data-action="skip"'));
const choicesBefore=run('JSON.stringify(optionsFor(current()))');
run("selection=optionsFor(current())[0];window.scrollY=720;changePaperLanguage('en')");assert.equal(ctx.scrollCalls.at(-1)[1],720);assert(app.innerHTML.includes('Unique English title'));assert(!app.innerHTML.includes('固有の日本語題名'));assert(!app.innerHTML.includes('Unique English abstract'));assert(run('selection!==null'));assert.equal(run('paperLang'),'en');
run("state.answers[current().id]={first:selection};selection=null;render()");assert(app.innerHTML.includes('Unique English abstract'));assert(!app.innerHTML.includes('固有の日本語要旨'));assert(!app.innerHTML.includes('data-action="skip"'));
run('skipPaper()');assert.equal(run('state.index'),0);assert(!run('state.answers[current().id].skipped'));
run("changePaperLanguage('ja')");assert(app.innerHTML.includes('固有の日本語要旨'));assert(!app.innerHTML.includes('Unique English abstract'));assert.equal(run('JSON.stringify(optionsFor(current()))'),choicesBefore);
run("state.answers={};state.index=0;selection=null;render();skipPaper()");assert.equal(run('state.index'),1);assert(run('state.answers[papers[0].id].skipped'));assert(!run('allComplete()'));
run("for(const p of papers.slice(1,5))state.answers[p.id]={first:p.journal,final:p.journal};state.index=5;state.screen='summary';render()");assert(app.innerHTML.includes('スキップ：1'));assert(app.innerHTML.includes(' / 4</small>'));assert(!app.innerHTML.includes(' / 5</small>'));
run("for(const p of papers.slice(0,5))state.answers[p.id]={skipped:true};render()");assert(app.innerHTML.includes('スキップ：5'));assert(app.innerHTML.includes(' / 0</small>'));assert(!app.innerHTML.includes('data-action="replay"'));
run("persist();state=read(key,{});for(const p of papers.slice(5))state.answers[p.id]={skipped:true};state.batch=1;state.index=2;render()");assert(run('allComplete()'));assert(app.innerHTML.includes('2周目へ'));
run('replay();state.screen="quiz";render()');assert.equal(run('Object.keys(state.answers).length'),0);assert(app.innerHTML.includes('data-action="skip"'));
console.log('Single-language rendering, persistent language, preserved choices, skips, score exclusion and replay passed.');

// Restart resets the active mode only, keeps saved papers and starts at paper one.
run("changeContent('journals');state={batch:1,index:1,screen:'home',answers:{[papers[0].id]:{skipped:true}},lap:3,history:[{lap:2,answers:{}}]};saved.preserve={id:'preserve'};persist();home()");
assert(app.innerHTML.includes('data-action="restart"'));
run("changeMode('professional');state.answers[papers[0].id]={first:'Nature'};persist();changeMode('beginner');restartProgress()");
assert.equal(run('state.batch'),0);assert.equal(run('state.index'),0);assert.equal(run('state.lap'),1);assert.equal(run('Object.keys(state.answers).length'),0);assert.equal(run('state.history'),undefined);assert.equal(run('state.screen'),'quiz');assert(run('Boolean(saved.preserve)'));assert.equal(run('selection'),null);
run('home()');assert(!app.innerHTML.includes('data-action="restart"'));
run("changeMode('professional')");assert.equal(run('Object.keys(state.answers).length'),1);
run("changeContent('biorxiv');state.answers[current().id]={final:'read'};state.lap=4;state.screen='home';persist();home()");assert(app.innerHTML.includes('data-action="restart"'));
run('restartProgress()');assert.equal(run('state.lap'),1);assert.equal(run('state.index'),0);assert(!run('allComplete()'));assert(app.innerHTML.includes('掲載先を予測してみてください'));assert(run('Boolean(saved.preserve)'));
console.log('Start-over resets only active-mode progress, preserves saved papers and starts at the first paper.');

run("paperLanguageManuallyChosen=false;changeUILanguage('en')");assert.equal(run('paperLang'),'en');assert.equal(run('uiLang'),'en');
run("changeUILanguage('ja')");assert.equal(run('paperLang'),'ja');
run("changePaperLanguage('en');changeUILanguage('en');changeUILanguage('ja')");assert.equal(run('paperLang'),'en');assert.equal(run('uiLang'),'ja');
for(const lang of ['ja','en']){
 const initialStorage=new Map([['paper-current-ui-language',JSON.stringify(lang)],['paper-current-paper-language',JSON.stringify(lang==='ja'?'en':'ja')]]);
 const fresh=vm.createContext({console,document,window:{PAPER_DATA:data,scrollTo(){}},localStorage:{getItem:k=>initialStorage.get(k),setItem:(k,v)=>initialStorage.set(k,v)},location:{search:'',pathname:'/'},history:{replaceState(){}},URLSearchParams});
 vm.runInContext(fs.readFileSync('docs/journal-options.js','utf8'),fresh);vm.runInContext(source,fresh);
 assert.equal(vm.runInContext('paperLang',fresh),lang);assert.equal(vm.runInContext('paperLanguageManuallyChosen',fresh),false);
}
console.log('Initial paper language follows page settings; manual language choices remain independent.');

run("changeUILanguage('ja');changeContent('journals');state.answers[papers[0].id]={skipped:true};state.screen='home';home()");
for(const id of ['content-help-journals','content-help-biorxiv','difficulty-help-beginner','difficulty-help-professional','restart-help']){
 assert(app.innerHTML.includes('aria-describedby="'+id+'"'));assert(app.innerHTML.includes('id="'+id+'" role="tooltip"'));
}
assert(!app.innerHTML.includes('<p class="hint">現在のモードの回答'));
assert(!run('modePicker()').includes('<p class="hint">'));
assert(app.innerHTML.includes('初心者モード。モードごとに進捗を保存します。'));
run("changeUILanguage('en')");assert(app.innerHTML.includes('Starting over resets answers and progress for this mode. Saved papers are kept.'));assert(!app.innerHTML.includes('現在のモードの回答'));
const tooltipClasses=new Set(),tooltipWrap={classList:{add:name=>tooltipClasses.add(name),remove:name=>tooltipClasses.delete(name)}};
app.querySelectorAll=selector=>selector==='.tooltip-wrap'?[tooltipWrap]:[];
run('bindTooltips()');tooltipWrap.onkeydown({key:'Escape'});assert(tooltipClasses.has('tooltip-dismissed'));tooltipWrap.onmouseenter();assert(!tooltipClasses.has('tooltip-dismissed'));tooltipWrap.onkeydown({key:'Escape'});tooltipWrap.onfocusin();assert(!tooltipClasses.has('tooltip-dismissed'));
app.querySelectorAll=()=>[];
console.log('Mode and restart descriptions are tooltips, localized, focusable and Escape-dismissable.');

// Selecting or changing a guess must leave the mounted page and scroll untouched.
const choiceButtons=Array.from({length:4},(_,i)=>({dataset:{option:String(i)},classList:{toggle(name,value){this[name]=value}},setAttribute(name,value){this[name]=value}}));
const confirmButton={disabled:true};
app.querySelectorAll=selector=>selector==='[data-action="choice"]'?choiceButtons:selector==='[data-action="confirm"]'?[confirmButton]:[];
for(const stage of ['title','abstract']){
 ctx.testStage=stage;
 run("changeContent('journals');state={batch:0,index:0,screen:'quiz',answers:{}};if(testStage==='abstract')state.answers[papers[0].id]={first:optionsFor(papers[0])[0]};selection=null;quiz()");
 const mountedHTML=app.innerHTML,scrollCount=ctx.scrollCalls.length;
 for(const index of [1,3,0]){
  choiceButtons[index].onclick();
  assert.equal(app.innerHTML,mountedHTML);assert.equal(ctx.scrollCalls.length,scrollCount);
  assert.equal(run('selection'),run('optionsFor(current())')[index]);assert.equal(confirmButton.disabled,false);
  choiceButtons.forEach((button,i)=>{assert.equal(button.classList.selected,i===index);assert.equal(button['aria-pressed'],String(i===index))});
 }
}
app.querySelectorAll=()=>[];
console.log('Title and abstract choices update in place without scrolling or replacing buttons.');

// Render scientific title formatting without accepting arbitrary HTML or attributes.
ctx.formattedTitle='<i>Kribbella</i>属と<i>Kribbella polygonati</i> sp. nov.';
assert.equal(run('titleHTML(formattedTitle)'),ctx.formattedTitle);
assert.equal(run("titleHTML('<EM>Species</EM> H<sub>2</sub>O 10<sup>2</sup> & text')"),'<em>Species</em> H<sub>2</sub>O 10<sup>2</sup> &amp; text');
assert.equal(run("titleHTML('<img src=x onerror=alert(1)><script>alert(1)</script>')"),'&lt;img src=x onerror=alert(1)&gt;&lt;script&gt;alert(1)&lt;/script&gt;');
assert.equal(run(`titleHTML('<i onclick="alert(1)">Species</i>')`),'&lt;i onclick=&quot;alert(1)&quot;&gt;Species</i>');
run("changeContent('journals');state={batch:0,index:0,screen:'quiz',answers:{}};paperLang='ja';papers[0].title_ja=formattedTitle;quiz()");
assert(app.innerHTML.includes(ctx.formattedTitle));assert.equal(run('current().title_ja'),ctx.formattedTitle);
run("state.answers[current().id]={first:current().journal,final:current().journal};summary()");assert(app.innerHTML.includes(ctx.formattedTitle));
run("saved[current().id]={...current()};savedView()");assert(app.innerHTML.includes(ctx.formattedTitle));
console.log('Scientific title formatting renders in quiz, summary and saved views; arbitrary HTML remains escaped.');

// Daily additions preserve progress and resume within a formerly partial round.
run("switchIssue(INITIAL_DATA,false);changeContent('journals');DATA.issue.publication_mode='daily';DATA.choice_context={catalog:DATA.journal_catalog||[],papers:papers.map(p=>({answer_journal:p.answer_journal,options:p.options}))};state={batch:1,index:2,screen:'summary',answers:{}};for(const p of papers)state.answers[p.id]={first:p.journal,final:p.journal};selection=null");
ctx.dailyPaper={...data.papers[0],id:'10.1234/daily',doi:'10.1234/daily'};
run('DATA.papers.push(dailyPaper);papers=selectPapers(DATA);summary()');
assert(app.innerHTML.includes('data-action="more"'));
const oldAnswers=run('JSON.stringify(state.answers)');
run('resumeUnanswered()');assert.equal(run('current().id'),'10.1234/daily');assert.equal(run('state.batch'),1);assert.equal(run('state.index'),2);assert.equal(run('JSON.stringify(state.answers)'),oldAnswers);
const dailyOptions=run('JSON.stringify(optionsFor(current()))');
run("DATA.journal_catalog.push({name:'New daily catalog journal',scope:['ecology']});papers.push({...current(),id:'more-later'});optionsFor(current())");assert.equal(run('JSON.stringify(optionsFor(current()))'),dailyOptions);
// A completed five-paper batch resumes correctly at the next batch boundary.
run("state.answers[current().id]={first:current().journal,final:current().journal};resumeUnanswered()");assert.equal(run('current().id'),'more-later');
run("DATA.issue.updated_at='2026-11-10T09:00:00+09:00';DATA.issue.added_date=new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'});DATA.issue.added_ids=['more-later'];uiLang='ja'");assert(run('updateNotice()').includes('本日追加 1本'));
// Weekly archive availability switches at Monday midnight JST, including year boundaries.
run("archiveIndex={archive_policy:'weekly',issues:[{id:'2026-W46',date:'2026-11-09'},{id:'2026-W47',date:'2026-11-16'}]};Date.now=()=>Date.parse('2026-11-15T14:59:59Z')");assert.equal(run('archivedEntries().length'),0);
run("Date.now=()=>Date.parse('2026-11-15T15:00:00Z')");assert.equal(run('archivedEntries().length'),1);assert.equal(run('archivedEntries()[0].id'),'2026-W46');
run("archiveIndex.issues=[{id:'2026-W53',date:'2026-12-28'}];Date.now=()=>Date.parse('2027-01-03T15:00:00Z')");assert.equal(run('archivedEntries().length'),1);
console.log('Daily append resumes partial rounds, preserves choices and answers, and archives at JST week boundaries.');

// Native sharing is optional; share plain title text and the paper DOI URL.
assert.equal(run('shareButton(current())'),'');
const expectedShareTitle=run("localizedTitle(current()).replace(/<[^>]*>/g,'')"),expectedShareURL=run('link(current())');
let sharedPayload;ctx.navigator={share:async payload=>{sharedPayload=payload}};
assert(run('shareButton(current())').includes('data-action="share"'));
const shareStatus={textContent:''};ctx.shareTestButton={parentElement:{querySelector:()=>shareStatus}};
(async()=>{
 await run('sharePaper(current(),shareTestButton)');
 assert.equal(sharedPayload.url,expectedShareURL);assert.equal(sharedPayload.title,expectedShareTitle);
 ctx.navigator.share=async()=>{throw Object.assign(new Error('cancel'),{name:'AbortError'})};
 await run('sharePaper(current(),shareTestButton)');assert.equal(shareStatus.textContent,'');
 ctx.navigator.share=async()=>{throw new Error('unavailable')};
 await run('sharePaper(current(),shareTestButton)');assert(shareStatus.textContent.length>0);
 console.log('Native share payload, unavailable browsers, cancellation and failure feedback passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
