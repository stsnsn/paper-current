const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const cytoscape=require('../docs/vendor/cytoscape-3.33.1.min.js');
(async()=>{
 const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,style:{},attributes:{},clientWidth:900,setAttribute(k,v){this.attributes[k]=v},removeAttribute(k){delete this.attributes[k]},scrollIntoView(){},focus(){}});return elements.get(id)};
 for(const [id,value] of [['node-count','40'],['min-edge','2'],['measure','count'],['timeline-mode','line'],['date-field','publication'],['sort','added']])get(id).value=value;
 let lastCy,lastChart;
 class Chart{constructor(canvas,config){this.config=config;lastChart=this}destroy(){}resize(){}}
 const context=vm.createContext({window:{PaperExplorer:require('../docs/explorer-core'),cytoscape:opts=>(lastCy=cytoscape({...opts,elements:JSON.parse(JSON.stringify(opts.elements)),style:JSON.parse(JSON.stringify(opts.style)),layout:{...opts.layout},container:undefined,headless:true,styleEnabled:true})),Chart},localStorage:{getItem:()=>null,setItem(){}},document:{documentElement:{},getElementById:get,querySelectorAll:()=>[]},URL,URLSearchParams,Date,Map,Set,console,location:{href:'http://localhost/explore.html?year=2026&query=SAR11',search:'?year=2026&query=SAR11'},history:{replaceState(){}},fetch:async file=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join('docs',file),'utf8'))})});
 vm.runInContext(fs.readFileSync('docs/explorer-i18n.js','utf8'),context);
 vm.runInContext(fs.readFileSync('docs/explorer.js','utf8'),context);
 for(let i=0;i<50&&!get('status').textContent.includes('一致');i++)await new Promise(resolve=>setImmediate(resolve));
 assert.match(get('status').textContent,/本が一致/);assert.equal(get('analysis-panel').hidden,true);assert.equal(lastCy,undefined);assert.match(get('results').innerHTML,/SAR11/i);assert.match(get('results').innerHTML,/https:\/\/doi.org\//);
 // Period modes cannot accidentally intersect a year and a custom date range.
 assert.equal(get('period').value,'year:2026');assert.equal(get('custom-period').hidden,true);assert.equal(get('start').disabled,true);
 get('start').value='2025-01-01';get('end').value='2025-12-31';assert.equal(vm.runInContext('criteria().start',context),'');assert.equal(vm.runInContext('criteria().year',context),'2026');
 get('period').value='range';get('period').onchange();assert.equal(get('custom-period').hidden,false);assert.equal(vm.runInContext('criteria().year',context),'');assert.equal(vm.runInContext('criteria().start',context),'2025-01-01');
 get('period').value='year:2026';get('period').onchange();assert.equal(get('start').value,'');assert.equal(get('end').value,'');
 get('kind').value='review';get('kind').onchange();assert.equal(get('advanced-count').textContent,'1');get('kind').value='';get('kind').onchange();assert.equal(get('advanced-count').textContent,'');
 get('tab-analysis').onclick();assert.equal(get('search-panel').hidden,true);assert.equal(get('analysis-panel').hidden,false);assert.ok(lastCy.nodes().length);assert.equal(lastCy.userPanningEnabled(),true);assert.equal(lastCy.userZoomingEnabled(),true);assert.equal(lastCy.nodes()[0].grabbable(),true);
 assert.match(get('reading-language').innerHTML,/class="tabs"/);assert.match(get('reading-language').innerHTML,/class="chosen"/);assert.equal(get('measure').value,'count');assert.equal(get('timeline-mode').value,'line');
 get('paper-en').onclick();assert.equal(vm.runInContext('paperLanguage',context),'en');get('paper-ja').onclick();assert.equal(vm.runInContext('paperLanguage',context),'ja');vm.runInContext('paperLanguageManuallyChosen=false',context);
 assert.match(get('term-list').innerHTML,/aria-pressed/);assert.match(get('future').innerHTML,/未来日付/);assert.match(get('timeline-table').innerHTML,/<table>/);assert.equal(lastChart.config.type,'line');assert.equal(lastChart.config.options.interaction.mode,'index');
 const originalCy=lastCy,selectedTerms=vm.runInContext('stats.ranked.slice(0,15).map(n=>n.term)',context);
 for(const term of selectedTerms)if(!vm.runInContext('selected',context).includes(term)){context.testTerm=term;vm.runInContext('toggleTerm(testTerm)',context)}
 assert.ok(vm.runInContext('selected.length',context)>=15);assert.equal(lastCy,originalCy);assert.equal(get('timeline-mode').value,'heatmap');assert.match(get('heatmap').innerHTML,/heatmap-table/);
 // Fixed palette, stable assignments and styles beyond the first eight colours.
 const colours=Array.from(vm.runInContext('selected.slice(0,8).map(termColor)',context));assert.equal(new Set(colours).size,8);assert.deepEqual(colours,['#0072B2','#D55E00','#009E73','#CC79A7','#A67600','#332288','#882255','#444444']);
 const term=selectedTerms[0];context.paletteTerm=term;const before=vm.runInContext('termColor(paletteTerm)',context);vm.runInContext('toggleTerm(paletteTerm);toggleTerm(paletteTerm)',context);assert.equal(vm.runInContext('termColor(paletteTerm)',context),before);
 get('timeline-mode').value='line';get('timeline-mode').onchange();assert.ok(lastChart.config.data.datasets.some(d=>d.borderDash.length>0));
 for(const n of lastCy.nodes())assert.ok(Math.abs(n.data('size')**2/n.data('count')-lastCy.nodes()[0].data('size')**2/lastCy.nodes()[0].data('count'))<.00001);
 const edges=lastCy.edges().toArray().sort((a,b)=>a.data('count')-b.data('count'));for(let i=1;i<edges.length;i++)assert.ok(edges[i].data('width')>=edges[i-1].data('width'));
 if(edges.length){edges[0].emit('tap');assert.match(get('network-detail').innerHTML,/共起/)}
 get('languageBtn').onclick();assert.equal(vm.runInContext('uiLang',context),'en');assert.equal(get('languageBtn').textContent,'UI: 日本語');assert.equal(get('savedBtn').textContent,'Read later 0');assert.equal(vm.runInContext('paperLanguage',context),'en');get('languageBtn').onclick();assert.equal(get('languageBtn').textContent,'UI: English');
 get('terms-clear').onclick();assert.equal(vm.runInContext('selected.length',context),0);
 const node=lastCy.nodes()[0];node.emit('tap');assert.equal(vm.runInContext('selected.length',context),1);assert.match(get('network-detail').innerHTML,/この語の論文を見る/);get('node-papers').onclick();assert.equal(get('search-panel').hidden,false);assert.equal(get('analysis-panel').hidden,true);assert.match(get('term-filter').innerHTML,/で絞り込み/);
 get('clear-term').onclick();get('tab-analysis').onclick();get('network-layout').onclick();get('network-fit').onclick();get('network-in').onclick();get('network-out').onclick();
 get('query').value='nonexistent-query-xyz123';await vm.runInContext('search()',context);assert.match(get('status').textContent,/0本/);assert.match(get('results').innerHTML,/一致する論文がありません/);
 get('period').value='range';get('period').onchange();get('start').value='2026-11-07';get('end').value='2026-01-01';await vm.runInContext('search()',context);assert.match(get('status').textContent,/開始日/);
 if(lastCy)lastCy.destroy();
 const html=fs.readFileSync('docs/explore.html','utf8');assert.equal((html.match(/class="secondary explorer-nav-link"/g)||[]).length,4);assert.ok(html.includes('class="page-heading"'));assert.ok(html.includes('id="reading-language" class="latest-floating"'));assert.match(html, /id="measure"><option value="count">/);assert.match(html, /id="timeline-mode"><option value="line">/);assert.ok(html.includes('vendor/cytoscape-3.33.1.min.js'));assert.ok(html.includes('id="languageBtn"'));assert.ok(!html.includes('新着論文へ</a>'));assert.ok(html.includes('新着論文を読む</a>'));
 console.log('Explorer tabs, real Cytoscape interactions, unlimited comparison, heatmap, chart tooltips, paper drilldown and shared navigation passed.');
})().catch(error=>{console.error(error);process.exit(1)});
