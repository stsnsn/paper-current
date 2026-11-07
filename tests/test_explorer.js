const assert=require('node:assert/strict'),E=require('../docs/explorer-core.js');
const papers=[
{id:'a',title:'SAR11 and dissolved organic matter',title_ja:'海洋の有機物',abstract:'marine carbon',date:'2026-05-01',collected_date:'2026-11-07',journal:'mBio',terms:['SAR11','carbon','carbon']},
{id:'b',title:'SAR11 phage',abstract:'marine viruses',date:'2026-07-01',collected_date:'2026-11-07',journal:'Nature',preprint:true,terms:['SAR11','phage']},
{id:'c',title:'Future ocean',abstract:'carbon',date:'2027-01-01',terms:['carbon','phage']},
{id:'d',title:'Undated marine paper',abstract:'marine',terms:['carbon']}
];
assert.deepEqual(E.filter(papers,{year:'2026',query:'SAR11 marine'}).map(p=>p.id),['a','b']);
assert.equal(E.filter(papers,{query:'海洋 有機物'}).length,1);
assert.equal(E.filter(papers,{year:'2027'}).length,1);
assert.equal(E.filter(papers,{dateField:'collected',year:'2026',start:'2026-11-01'}).length,2);
assert.equal(E.filter(papers,{year:'2026',kind:'journal',journal:'mBio'}).length,1);
assert.equal(E.filter(papers,{start:'2026-06-01',end:'2026-07-01'}).length,1);
const stats=E.statistics(papers);assert.equal(stats.ranked.find(n=>n.term==='carbon').count,3);assert.equal(stats.ranked.find(n=>n.term==='SAR11').share,.5);assert.equal(stats.edges.find(e=>e.a==='SAR11'&&e.b==='carbon').count,1);
const series=E.timeline(papers,['SAR11'],'2026-11-07');assert.deepEqual(series.months.map(m=>m.month),['2026-05','2026-06','2026-07']);assert.equal(series.months[1].total,0);assert.equal(series.months[0].values[0].share,1);assert.deepEqual(series.future.map(p=>p.id),['c']);assert.deepEqual(series.unknown.map(p=>p.id),['d']);
assert.deepEqual(E.statistics([]).nodes,[]);assert.deepEqual(E.timeline([],[],'2026-11-07').months,[]);
console.log('Explorer bilingual AND search, filters, binary co-occurrence, monthly denominators, missing months and future separation passed.');
