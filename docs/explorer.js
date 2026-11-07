'use strict';
const E=window.PaperExplorer,$=id=>document.getElementById(id),escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let cy=null,trendChart=null,resizeObserver=null,activePanel='search',networkDetail=null;
let paperLanguageManuallyChosen=false;
let appliedCriteria={},manifest,baseRows=[],matched=[],selected=[],page=1,request=0,stats,termOnly='',paperLanguage='ja';
const cache=new Map(),today=()=>new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'});
let uiLang='ja';
try{uiLang=JSON.parse(localStorage.getItem('paper-current-ui-language'))==='en'?'en':'ja'}catch{}
paperLanguage=uiLang;
const t=value=>uiLang==='en'?window.ExplorerI18n.translate(value):value;
const translateInterface=window.ExplorerI18n.install(document,()=>uiLang);
function updateHeader(){
 $('languageBtn').textContent=uiLang==='ja'?'UI: English':'UI: 日本語';$('languageBtn').lang=uiLang==='ja'?'en':'ja';
 let count=0;try{count=Object.keys(JSON.parse(localStorage.getItem('paper-current-saved')||'{}')).length}catch{}
 $('savedBtn').textContent=(uiLang==='ja'?'あとで読む ':'Read later ')+count;
 document.title=uiLang==='ja'?'全体検索・解析 — Paper Current':'Search & explore — Paper Current';
 translateInterface();
}
function changeUILanguage(next){
 if(!['ja','en'].includes(next))return;
 uiLang=next;try{localStorage.setItem('paper-current-ui-language',JSON.stringify(uiLang))}catch{}
 if(!paperLanguageManuallyChosen)paperLanguage=uiLang;
 if(stats){renderFilterSummary();renderResults();if(activePanel==='analysis')renderAnalysis(false)}
 if(networkDetail){if(networkDetail.type==='node')showNodeDetails(networkDetail.value);else showEdgeDetails(networkDetail.value)}
 updateHeader();
}
$('languageBtn').onclick=()=>changeUILanguage(uiLang==='ja'?'en':'ja');
$('savedBtn').onclick=()=>{location.href='./?saved=1'};
updateHeader();
function criteria(){
 const period=$('period').value,range=period==='range';
 return {query:$('query').value,year:period.startsWith('year:')?period.slice(5):'',dateField:$('date-field').value,start:range?$('start').value:'',end:range?$('end').value:'',kind:$('kind').value,journal:$('journal').value};
}
function updateFilterControls(){
 $('period-label').textContent=$('date-field').value==='collected'?'取り込み期間':'公開期間';
 const range=$('period').value==='range';$('custom-period').hidden=!range;
 $('start').disabled=$('end').disabled=!range;
 if(!range){$('start').value='';$('end').value=''}
 const count=Number(Boolean($('kind').value))+Number(Boolean($('journal').value))+Number($('date-field').value==='collected');
 $('advanced-count').textContent=count?String(count):'';
}
function renderFilterSummary(){
 const f=appliedCriteria,parts=[];
 parts.push(f.year?f.year+'年':f.start||f.end?`${f.start||'…'} — ${f.end||'…'}`:'すべての期間');
 if(f.kind)parts.push(({journal:'雑誌論文',review:'レビュー',preprint:'プレプリント'})[f.kind]);
 if(f.journal)parts.push(f.journal);
 if(f.dateField==='collected')parts.push('サイト取り込み日');
 $('filter-summary').innerHTML=parts.map(part=>`<span>${escapeHTML(t(part))}</span>`).join('');
}
async function fetchJSON(path){const response=await fetch(path);if(!response.ok)throw Error(`HTTP ${response.status}`);return response.json()}
function syncURL(){const url=new URL(location.href);url.search='';const f=appliedCriteria;for(const [k,v] of Object.entries(f))if(v&&!(k==='dateField'&&v==='publication'))url.searchParams.set(k,v);if(activePanel==='analysis')url.searchParams.set('panel','analysis');history.replaceState(null,'',url)}
async function search(){
 const serial=++request,f=criteria();
 if(f.start&&f.end&&f.start>f.end){$('status').textContent='開始日は終了日以前にしてください。';$('workspace').hidden=true;$('explore-form').removeAttribute('aria-busy');return}
 $('status').textContent='検索データを読み込んでいます…';$('workspace').hidden=true;$('explore-form').setAttribute('aria-busy','true');
 try{
  const years=manifest.years.filter(y=>f.dateField==='collected'||!f.year||y.year===f.year);
  const values=await Promise.all(years.map(async y=>{if(!cache.has(y.path))cache.set(y.path,fetchJSON(y.path).catch(error=>{cache.delete(y.path);throw error}));return cache.get(y.path)}));
  if(serial!==request)return;
  appliedCriteria={...f};baseRows=values.flat();matched=E.filter(baseRows,f);stats=E.statistics(matched,Number($('node-count').value));selected=[];termOnly='';page=1;
  termSlots.clear();selected=stats.ranked.slice(0,3).map(n=>n.term);selected.forEach(termSlot);syncURL();renderFilterSummary();$('workspace').hidden=false;$('status').textContent=`${matched.length.toLocaleString()}本が一致しました。`;
  if(cy){cy.destroy();cy=null}if(trendChart){trendChart.destroy();trendChart=null}renderResults();switchPanel(activePanel);$('search-tab-count').textContent=matched.length+'本';
 }catch(error){if(serial===request){$('status').innerHTML='読み込みに失敗しました。通信を確認し、検索ボタンで再試行してください。';console.error(error)}}
 finally{if(serial===request)$('explore-form').removeAttribute('aria-busy')}
}
// Reserve palette slots for the search session so a term never changes colour on deselection.
const SERIES_PALETTE=['#0072B2','#D55E00','#009E73','#CC79A7','#A67600','#332288','#882255','#444444'];
const SERIES_DASHES=[[],[7,4],[2,3],[10,3,2,3]];
const termSlots=new Map();
function termSlot(term){if(!termSlots.has(term))termSlots.set(term,termSlots.size);return termSlots.get(term)}
function termColor(term){return SERIES_PALETTE[termSlot(term)%SERIES_PALETTE.length]}
function termDash(term){return SERIES_DASHES[Math.floor(termSlot(term)/SERIES_PALETTE.length)%SERIES_DASHES.length]}
function nodeDiameter(count){return 54*Math.sqrt(count/Math.max(1,...stats.nodes.map(n=>n.count)))}
function edgeWidth(count){return 1+6*(count/Math.max(1,...stats.edges.map(e=>e.count)))}

function switchPanel(next){
 activePanel=next==='analysis'?'analysis':'search';
 for(const name of ['search','analysis']){const active=name===activePanel;$(`${name}-panel`).hidden=!active;$(`tab-${name}`).setAttribute('aria-selected',String(active));$(`tab-${name}`).setAttribute('tabindex',active?'0':'-1')}
 if(activePanel==='analysis'){renderAnalysis(!cy);if(cy)cy.resize();if(trendChart)trendChart.resize()}
 syncURL();
}
function toggleTerm(term){
 if(selected.includes(term))selected=selected.filter(t=>t!==term);else{termSlot(term);selected.push(term)}
 if(selected.length===9)$('timeline-mode').value='heatmap';
 renderAnalysis(false);
}
function bindTerms(){document.querySelectorAll('[data-term]').forEach(el=>{el.onclick=()=>toggleTerm(el.dataset.term)})}
function renderTermPicker(){
 const q=E.normalize($('term-query').value);
 const ranked=stats.ranked.filter(n=>!q||E.normalize(n.term).includes(q));
 $('selection-count').textContent=`${selected.length}語を選択中`;
 $('term-list').innerHTML=ranked.slice(0,200).map(n=>`<button type="button" data-term="${escapeHTML(n.term)}" aria-pressed="${selected.includes(n.term)}">${escapeHTML(n.term)} <span>${n.count}本 · ${(n.share*100).toFixed(1)}%</span></button>`).join('')||'<p class="hint">一致する語がありません。</p>';
 if(ranked.length>200)$('term-list').innerHTML+='<p class="hint">上位200語を表示しています。語を入力するとさらに絞れます。</p>';
 bindTerms();
}
function renderAnalysis(rebuild=true){
 const series=E.timeline(matched,selected,today()),dated=matched.length-series.future.length-series.unknown.length;
 $('analysis-context').textContent=`${appliedCriteria.query?`「${appliedCriteria.query}」 · `:''}${matched.length.toLocaleString()}本を解析中。検索結果タブに戻っても条件は維持されます。`;
 $('metrics').innerHTML=[['対象論文',matched.length+'本'],['抽出語句',stats.ranked.length.toLocaleString()+'語'],['公開日が今日まで',dated+'本'],['先行公開・未来日付',series.future.length+'本']].map(([label,value])=>`<div><span>${label}</span><strong>${value}</strong></div>`).join('');
 if(rebuild||!cy)renderNetwork();else updateNetworkSelection();
 renderTermPicker();
 $('selected-terms').innerHTML=selected.map(term=>`<button type="button" data-term="${escapeHTML(term)}" class="selected-term" style="--term-color:${termColor(term)}" aria-label="${escapeHTML(term)}の選択を解除">${escapeHTML(term)} ×</button>`).join('')||'<p class="hint">地図または語の一覧から比較する語を選んでください。</p>';
 renderTimeline(series);
 $('future').innerHTML=`<strong>先行公開・未来日付：${series.future.length}本</strong><p>検索・共起集計には含み、月別推移には含めていません。日付不明：${series.unknown.length}本。</p>${series.future.length?'<button type="button" id="show-future" class="quiet">未来日付の論文を見る →</button>':''}`;
 if($('show-future'))$('show-future').onclick=()=>{termOnly='@future';page=1;renderResults();switchPanel('search')};
 bindTerms();
}
function layoutOptions(){return {name:'cose',animate:false,fit:true,padding:55,nodeDimensionsIncludeLabels:true,nodeRepulsion:()=>11000,idealEdgeLength:()=>140,gravity:.15,numIter:500,randomize:false}}
function renderNetwork(){
 if(cy){cy.destroy();cy=null}
 $('network').innerHTML='';networkDetail=null;$('network-detail').textContent='語を選ぶと、論文数と関連語を表示します。';
 if(!stats.nodes.length){$('network').innerHTML='<p class="chart-empty">検索に一致する論文がありません。</p>';return}
 if(!window.cytoscape){$('network').innerHTML='<p class="notice">ネットワークのライブラリを読み込めませんでした。ページを再読み込みしてください。</p>';return}
 const nodeIds=new Map(stats.nodes.map((n,i)=>[n.term,'n'+i]));
 const elements=[...stats.nodes.map(n=>({data:{id:nodeIds.get(n.term),label:n.term,count:n.count,size:nodeDiameter(n.count),color:selected.includes(n.term)?termColor(n.term):'#78919f'}})),...stats.edges.filter(e=>e.count>=Number($('min-edge').value)).map((e,i)=>({data:{id:'e'+i,source:nodeIds.get(e.a),target:nodeIds.get(e.b),count:e.count,strength:e.strength,width:edgeWidth(e.count),opacity:.35+.6*e.strength}}))];
 cy=window.cytoscape({container:$('network'),elements,layout:layoutOptions(),minZoom:.15,maxZoom:4,boxSelectionEnabled:false,style:[
 {selector:'node',style:{label:'data(label)',width:'data(size)',height:'data(size)','background-color':'#78919f','border-width':1.5,'border-color':'#415e70','font-size':13,color:'#183346','text-wrap':'wrap','text-max-width':130,'text-valign':'bottom','text-margin-y':8,'text-background-color':'#fff','text-background-opacity':.85,'text-background-padding':3}},
 {selector:'edge',style:{width:'data(width)','line-color':'#536d80',opacity:'data(opacity)','curve-style':'haystack'}},
 {selector:'node.compared',style:{'background-color':'data(color)','border-color':'data(color)','border-width':3,'border-style':'double'}},
 {selector:'.dimmed',style:{opacity:.15}},
 {selector:'.focused',style:{'border-width':4,'border-color':'#183346'}}
 ]});
 cy.on('tap','node',event=>{const node=event.target,term=node.data('label');toggleTerm(term);showNodeDetails(term)});
 cy.on('tap','edge',event=>showEdgeDetails(event.target));
 cy.on('mouseover','node',event=>{const node=event.target;cy.elements().addClass('dimmed');node.closedNeighborhood().removeClass('dimmed');node.addClass('focused');$('network').style.cursor='pointer'});
 cy.on('mouseout','node',()=>{cy.elements().removeClass('dimmed focused');$('network').style.cursor='grab'});
 updateNetworkSelection();
 if(resizeObserver)resizeObserver.disconnect();
 if(typeof ResizeObserver!=='undefined'){resizeObserver=new ResizeObserver(()=>{if(cy&&activePanel==='analysis'&&$('network').clientWidth>0){cy.resize();cy.fit(undefined,50)}});resizeObserver.observe($('network'))}
}
function updateNetworkSelection(){if(cy)cy.nodes().forEach(node=>{node.data('color',selected.includes(node.data('label'))?termColor(node.data('label')):'#78919f');node.toggleClass('compared',selected.includes(node.data('label')))})}
function showEdgeDetails(edge){
 networkDetail={type:'edge',value:edge};
 const a=edge.source().data('label'),b=edge.target().data('label');
 $('network-detail').innerHTML=`<div><strong>${escapeHTML(a)} × ${escapeHTML(b)}</strong><p>${uiLang==='ja'?'共起する論文数：':'Co-occurring papers: '}${edge.data('count')} · ${uiLang==='ja'?'補正した共起の強さ：':'Normalized association: '}${edge.data('strength').toFixed(3)}</p></div>`;
}
function showNodeDetails(term){
 networkDetail={type:'node',value:term};
 const entry=stats.ranked.find(n=>n.term===term);if(!entry)return;
 const related=stats.edges.filter(e=>e.a===term||e.b===term).sort((a,b)=>b.count-a.count).slice(0,5).map(e=>`${e.a===term?e.b:e.a}（${e.count}本）`).join('、');
 $('network-detail').innerHTML=`<div><strong>${escapeHTML(term)}</strong> · ${entry.count}本（${(entry.share*100).toFixed(1)}%）<p>${related?'共起する語：'+escapeHTML(related):'表示中の語との共起はありません。'}</p></div><button type="button" id="node-papers" class="secondary">この語の論文を見る →</button>`;
 $('node-papers').onclick=()=>{termOnly=term;page=1;renderResults();switchPanel('search')};
}
function renderTimeline(series){
 if(trendChart){trendChart.destroy();trendChart=null}
 const rows=series.months,mode=$('measure').value,heat=$('timeline-mode').value==='heatmap';
 $('timeline').hidden=heat;$('heatmap').hidden=!heat;
 $('timeline-suggestion').textContent=selected.length>8?'多くの語を選択中です。ヒートマップに切り替えると一覧で比較できます。':'';
 if(!rows.length||!selected.length){$('timeline').innerHTML='<p class="chart-empty">語を選ぶと今日までの公開日の推移を表示します。</p>';$('heatmap').innerHTML='';$('timeline-table').innerHTML='';return}
 $('timeline-table').innerHTML=`<table><thead><tr><th>公開月</th><th>対象論文</th>${selected.map(t=>`<th>${escapeHTML(t)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr><th>${r.month}</th><td>${r.total}本</td>${r.values.map(v=>`<td>${v.count}本（${(v.share*100).toFixed(1)}%）</td>`).join('')}</tr>`).join('')}</tbody></table>`;
 const value=v=>mode==='count'?v.count:v.share*100,max=rows.reduce((max,r)=>r.values.reduce((m,v)=>Math.max(m,value(v)),max),1);
 if(heat){
  $('heatmap').innerHTML=`<table class="heatmap-table"><thead><tr><th>語句 / 公開月</th>${rows.map(r=>`<th>${r.month}<small>対象 ${r.total}本</small></th>`).join('')}</tr></thead><tbody>${selected.map((term,i)=>`<tr><th>${escapeHTML(term)}</th>${rows.map(r=>{const v=r.values[i],intensity=value(v)/max;return `<td style="background:rgba(8,107,136,${r.total ? .06+.84*intensity : 0});color:${intensity>.6?'#fff':'#183346'}" title="${escapeHTML(term)} · ${r.month}：${v.count}/${r.total}${uiLang==='ja'?'本':' papers'}（${(v.share*100).toFixed(1)}%）">${r.total?(mode==='count'?v.count:(v.share*100).toFixed(1)+'%'):'—'}</td>`}).join('')}</tr>`).join('')}</tbody></table>`;
  return;
 }
 $('timeline').innerHTML='<canvas id="trend-canvas" role="img" aria-label="選択語の月別推移。詳細は月別数値表を参照してください。"></canvas>';
 if(!window.Chart){$('timeline').innerHTML='<p class="notice">グラフを読み込めませんでした。数値表をご利用ください。</p>';return}
 trendChart=new window.Chart($('trend-canvas'),{type:'line',data:{labels:rows.map(r=>r.month),datasets:selected.map((term,i)=>({label:term,data:rows.map(r=>r.total?value(r.values[i]):null),borderColor:termColor(term),backgroundColor:termColor(term),borderWidth:2.5,borderDash:termDash(term),pointStyle:['circle','rect','triangle','rectRot'][Math.floor(termSlot(term)/SERIES_PALETTE.length)%4],pointRadius:3,pointHoverRadius:6,tension:.15,spanGaps:false}))},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:selected.length<=12,position:'bottom',labels:{boxWidth:12,padding:18,font:{size:12}}},tooltip:{callbacks:{title:items=>items.length?`${rows[items[0].dataIndex].month} · ${uiLang==='ja'?'対象 ':''}${rows[items[0].dataIndex].total}${uiLang==='ja'?'本':' papers'}`:'',label:item=>{const r=rows[item.dataIndex],v=r.values[item.datasetIndex];return `${item.dataset.label}：${v.count}/${r.total}${uiLang==='ja'?'本':' papers'}（${(v.share*100).toFixed(1)}%）`}}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12}},y:{beginAtZero:true,suggestedMax:mode==='share'?Math.min(100,max*1.1):undefined,title:{display:true,text:t(mode==='count'?'論文数':'対象論文に占める割合（%）')},ticks:mode==='count'?{precision:0}: {callback:v=>v+'%'}}}}});
}
function changePaperLanguage(next){
 const position=[window.scrollX||0,window.scrollY||0];paperLanguage=next;paperLanguageManuallyChosen=true;renderResults();window.scrollTo?.(...position);
}
function renderResults(){
 const openAbstracts=new Set([...document.querySelectorAll('#results details[open]')].map(el=>el.closest('[data-paper-id]').dataset.paperId));
 let rows=matched.filter(p=>termOnly==='@future'?p.date>today():!termOnly||(p.terms||[]).includes(termOnly));
 const added=p=>Date.parse(p.collected_at||p.collected_date||p.first_seen||'')||0;
 rows.sort((a,b)=>$('sort').value==='date'?String(b.date||'').localeCompare(String(a.date||'')):(added(b)-added(a))||((b.collection_order||0)-(a.collection_order||0)));
 $('result-count').textContent=rows.length+'本';
 $('term-filter').innerHTML=termOnly?`<span class="active-term">${termOnly==='@future'?'先行公開・未来日付':escapeHTML(termOnly)} で絞り込み <button id="clear-term" type="button" class="quiet">解除 ×</button></span>`:'';
 $('reading-language').innerHTML=`<div class="tabs" role="group" aria-label="論文の表示"><span class="language-label">論文の表示</span><button type="button" id="paper-ja" aria-pressed="${paperLanguage==='ja'}" class="${paperLanguage==='ja'?'chosen':''}" lang="ja">日本語</button><button type="button" id="paper-en" aria-pressed="${paperLanguage==='en'}" class="${paperLanguage==='en'?'chosen':''}" lang="en">English</button></div>`;
 if($('clear-term'))$('clear-term').onclick=()=>{termOnly='';page=1;renderResults()};
 $('paper-ja').onclick=()=>changePaperLanguage('ja');$('paper-en').onclick=()=>changePaperLanguage('en');
 $('results').innerHTML=rows.slice(0,page*30).map(p=>{const title=paperLanguage==='ja'?(p.title_ja||p.title):p.title,abstract=paperLanguage==='ja'?(p.abstract_ja||p.abstract):p.abstract;let href=p.doi?'https://doi.org/'+encodeURI(p.doi):p.source_url;if(!/^https?:\/\//i.test(href||''))href='';return `<article class="explore-paper" data-paper-id="${escapeHTML(p.id)}"><div class="paper-meta"><span>${escapeHTML(p.preprint?'プレプリント · '+(p.journal||''):p.journal)}</span><time>${escapeHTML(p.date||'公開日不明')}</time>${p.date>today()?'<span class="badge">未来日付</span>':''}</div><h3 lang="${paperLanguage}">${escapeHTML(title)}</h3><details${openAbstracts.has(p.id)?' open':''}><summary>要旨を読む</summary><p class="paper-abstract" lang="${paperLanguage}">${escapeHTML(abstract||'要旨はありません。')}</p></details><div class="paper-actions">${href?`<a href="${escapeHTML(href)}" target="_blank" rel="noopener">原論文を読む ↗</a>`:''}${p.issue?`<a href="./?issue=${encodeURIComponent(p.issue)}">収録週を見る →</a>`:''}</div></article>`}).join('')||'<p class="notice">一致する論文がありません。語句や期間を変えてみてください。</p>';
 $('more').hidden=rows.length<=page*30;
}
$('explorer-top').onclick=()=>window.scrollTo({top:0,left:0,behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
$('explore-form').onsubmit=event=>{event.preventDefault();search()};
$('reset').onclick=()=>{$('explore-form').reset();updateFilterControls();$('advanced-filters').open=false;search()};
$('period').onchange=updateFilterControls;
for(const id of ['kind','journal','date-field'])$(id).onchange=updateFilterControls;
$('node-count').onchange=()=>{stats=E.statistics(matched,Number($('node-count').value));renderAnalysis()};
$('min-edge').onchange=renderNetwork;
$('measure').onchange=$('timeline-mode').onchange=()=>renderTimeline(E.timeline(matched,selected,today()));
$('sort').onchange=renderResults;$('more').onclick=()=>{page++;renderResults()};
$('tab-search').onclick=$('back-results').onclick=()=>switchPanel('search');$('tab-analysis').onclick=()=>switchPanel('analysis');
for(const name of ['search','analysis'])$(`tab-${name}`).onkeydown=event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?'search':event.key==='End'?'analysis':name==='search'?'analysis':'search';switchPanel(next);$(`tab-${next}`).focus()}};
$('term-query').oninput=renderTermPicker;
$('terms-top').onclick=()=>{selected=stats.ranked.slice(0,10).map(n=>n.term);selected.forEach(termSlot);$('timeline-mode').value='heatmap';renderAnalysis(false)};
$('terms-clear').onclick=()=>{selected=[];renderAnalysis(false)};
$('network-in').onclick=()=>{if(cy)cy.zoom({level:Math.min(4,cy.zoom()*1.3),renderedPosition:{x:cy.width()/2,y:cy.height()/2}})};
$('network-out').onclick=()=>{if(cy)cy.zoom({level:Math.max(.15,cy.zoom()/1.3),renderedPosition:{x:cy.width()/2,y:cy.height()/2}})};
$('network-fit').onclick=()=>{if(cy){cy.resize();cy.fit(undefined,50)}};
$('network-layout').onclick=()=>{if(cy)cy.layout(layoutOptions()).run()};

(async()=>{try{manifest=await fetchJSON('data/explorer/index.json');$('corpus-count').textContent=`全${manifest.count.toLocaleString()}本 · アーカイブを含む`;
 const years=manifest.filter_years;$('period').innerHTML='<option value="">すべての期間</option>'+years.map(y=>`<option value="year:${escapeHTML(y)}">${escapeHTML(y)}年</option>`).join('')+'<option value="range">日付を指定…</option>';
 const params=new URLSearchParams(location.search);activePanel=params.get('panel')==='analysis'?'analysis':'search';const ids={query:'query',dateField:'date-field',start:'start',end:'end',kind:'kind',journal:'journal'};
 for(const [key,id] of Object.entries(ids))if(params.has(key)&&key!=='journal')$(id).value=params.get(key);
 if(params.has('start')||params.has('end'))$('period').value='range';else if(years.includes(params.get('year')))$('period').value='year:'+params.get('year');
 const journals=manifest.journals;$('journal').innerHTML='<option value="">すべての掲載誌</option>'+journals.map(j=>`<option value="${escapeHTML(j)}">${escapeHTML(j)}</option>`).join('');if(params.has('journal'))$('journal').value=params.get('journal');
 updateFilterControls();if($('advanced-count').textContent)$('advanced-filters').open=true;
 $('data-updated').textContent='検索データ更新：'+new Date(manifest.generated_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo'})+' JST';await search();
 }catch(error){$('status').textContent='検索データを読み込めませんでした。ページを再読み込みしてお試しください。';console.error(error)}})();
