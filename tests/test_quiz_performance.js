const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync('docs/journal-options.js','utf8'),ctx);
// A growing observed catalog must not repeat profile/distance work in the sort comparator.
vm.runInContext(`
const largeCatalog=Array.from({length:1500},(_,i)=>({name:'Observed venue '+i,scope:['microbiology'],if:1+i%20,year:2025}));
const testPaper={id:'performance-paper',journal:'mBio',tags:['海洋微生物']};
let distanceCalls=0;const originalDistance=journalDistance;
journalDistance=(...args)=>{distanceCalls++;return originalDistance(...args)};
`,ctx);
for(const mode of ['beginner','professional']){
 ctx.testMode=mode;
 const choices=vm.runInContext("distanceCalls=0;journalOptions(testPaper,[testPaper],testMode,'fixed-seed',largeCatalog)",ctx,{timeout:5000});
 assert.equal(choices.length,4);assert.equal(new Set(choices).size,4);assert(choices.includes('mBio'));
 assert(vm.runInContext('distanceCalls<=largeCatalog.length+Object.keys(JOURNAL_PROFILES).length',ctx));
 assert.deepEqual(choices,vm.runInContext("journalOptions(testPaper,[testPaper],testMode,'fixed-seed',largeCatalog)",ctx,{timeout:5000}));
}
console.log('Large journal catalogs generate deterministic choices with at most one distance calculation per candidate.');
