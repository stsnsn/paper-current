const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const app={innerHTML:'',querySelectorAll:()=>[]};
const ctx=vm.createContext({window:{PAPER_DATA:{issue:{id:'test'},papers:[]},scrollTo(){}},document:{documentElement:{},querySelector:s=>s==='#app'?app:{}},localStorage:{getItem:()=>null,setItem(){}},location:{search:'',pathname:'/'},history:{replaceState(){}},URLSearchParams});
const run=s=>vm.runInContext(s,ctx);
run(fs.readFileSync('docs/journal-options.js','utf8'));
run(fs.readFileSync('docs/data/journal-metrics.js','utf8'));
let source=fs.readFileSync('docs/app.js','utf8');run(source.slice(0,source.lastIndexOf('(async()=>')));
const metrics=JSON.parse(fs.readFileSync('config/quiz-journal-metrics.json','utf8')).journals;
assert.equal(run('Object.keys(JOURNAL_PROFILES).length'),92);
for(const metric of metrics){
 ctx.journalName=metric.name;
 assert.equal(run('journalProfile(journalName).if'),metric.value);
 assert(run('journalProfile(journalName).scope.length>0'));
 assert(metric.value>0&&Number.isFinite(metric.value));
 assert(metric.year&&metric.source&&metric.kind&&metric.checked_on);
}
assert.equal(run("journalProfile('ISME Host Microbe').if"),run("journalProfile('ISME Communications').if"));
assert.equal(run("journalProfile('Animal Microbiology').if"),run("journalProfile('Animal Microbiome').if"));
assert.equal(run("journalProfile('ASM Animal Microbiology').if_kind"),'proxy');
assert.equal(run("journalProfile('eLife').year"),2023);
// Historical values must contribute to quiz distances too.
assert(run("journalDistance({scope:['biology'],if:6.4,year:2023},{scope:['biology'],if:6.4,year:2025}) < journalDistance({scope:['biology'],if:6.4,year:2023},{scope:['biology'],if:20,year:2025})"));
// Quiz-only values never flow into displayed IFs or the display sorting map.
for(const name of ['ISME Host Microbe','Animal Microbiology','ASM Animal Microbiology','microLife','eLife']){
 ctx.journalName=name;
 assert.equal(run('paperImpact({journal:journalName})'),null);
 assert(!run('paperImpactHTML({journal:journalName})').includes('2025 IF'));
}
assert.equal(run('window.PAPER_JOURNAL_METRICS.journals.length'),43);
console.log('All 92 quiz IFs have provenance; proxies, aliases and historical weights work without entering displayed JIFs.');
