'use strict';
const INITIAL_DATA=window.PAPER_DATA,app=document.querySelector('#app');
let DATA=INITIAL_DATA,viewingArchive=false,archiveIndex=window.PAPER_ARCHIVES||null,archiveError=false,archiveLoading=false;
let storageOK=true,mountScrollPosition=null,archiveBrowserOpen=false;
function read(k,d){try{return JSON.parse(localStorage.getItem(k))||d}catch{return d}}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function canonicalDOI(value){let s=String(value||'');try{s=decodeURIComponent(s)}catch{}const m=s.match(/10\.\d{4,9}\/[^\s<>"?#]+/i);if(!m)return '';s=m[0].replace(/[.,;]+$/,'').toLowerCase();if((s.startsWith('10.1101/')||s.startsWith('10.64898/')))s=s.replace(/(?:v\d+)?(?:\.full(?:\.pdf)?|\.abstract)?\/?$/,'');return s}
const identities=p=>[p.doi,p.id,p.preprint_doi,p.published_doi,...(p.related_dois||[])].map(canonicalDOI).filter(Boolean);
// Defend against duplicate rows even in hand-edited issue JSON. Alias links are
// explicit metadata; similar titles alone never identify the same paper.
function uniquePapers(rows){const groups=[];for(const p of rows){let keys=new Set(identities(p));const matching=groups.filter(g=>[...keys].some(k=>g.keys.has(k)));if(!matching.length)groups.push({paper:p,keys});else{const first=matching[0];for(const g of matching){for(const k of g.keys)keys.add(k);if(g!==first)groups.splice(groups.indexOf(g),1)}first.keys=keys;}}return groups.map(g=>g.paper)}
let isDemo=DATA.papers.some(p=>p.demo)||DATA.issue.id.startsWith('prototype');
let contentMode=read('paper-current-content','latest');if(read('paper-current-home-version',0)<1){contentMode='latest';try{localStorage.setItem('paper-current-content',JSON.stringify(contentMode));localStorage.setItem('paper-current-home-version','1')}catch{}}if(!['journals','biorxiv','latest'].includes(contentMode))contentMode='latest';
const selectPapers=data=>uniquePapers(!viewingArchive&&data===INITIAL_DATA&&contentMode==='latest'&&Array.isArray(window.PAPER_RECENT_DATA)?window.PAPER_RECENT_DATA:data.papers).filter(p=>contentMode==='latest'||(contentMode==='biorxiv'?p.preprint:!p.preprint));
const stateKey=()=> 'paper-current-v1:'+DATA.issue.id+(contentMode==='latest'?':latest':contentMode==='biorxiv'?':biorxiv':mode==='professional'?':professional':'');
let papers=selectPapers(DATA),key='paper-current-v1:'+DATA.issue.id;
let mode=read('paper-current-mode','professional');if(!['beginner','professional'].includes(mode))mode='professional';
key=stateKey();
let state=read(key,{batch:0,index:0,screen:'home',answers:{}}),saved=read('paper-current-saved',{}),uiLang=read('paper-current-ui-language','ja'),selection=null;
if(!['ja','en'].includes(uiLang))uiLang='ja';
const t=(ja,en)=>uiLang==='ja'?ja:en;
let paperLang=uiLang,paperLanguageManuallyChosen=false;
const localizedTitle=p=>paperLang==='ja'?(p.title_ja||'日本語訳は準備中'):(p.title||'Title unavailable');
function paperLanguagePicker(){return `<div class="tabs" role="group" aria-label="${t('論文の表示','Paper display')}"><span class="language-label">${t('論文の表示','Paper display')}</span>${['ja','en'].map(lang=>`<button type="button" class="${paperLang===lang?'chosen':''}" data-action="paper-lang" data-paper-lang="${lang}" aria-pressed="${paperLang===lang}" lang="${lang}">${lang==='ja'?'日本語':'English'}</button>`).join('')}</div>`}
// Escape all input first; restore only attribute-free inline title formatting.
function titleHTML(value){return esc(value).replace(/&lt;(\/?)(i|em|b|strong|sub|sup)\s*&gt;/gi,(_,slash,tag)=>'<'+slash+tag.toLowerCase()+'>')}
function paperTitleHTML(p){return `<div class="${paperLang==='ja'?'title-ja':'title-en'}" lang="${paperLang}">${titleHTML(localizedTitle(p))}</div>`}
// Temporary display correction for the 33 audited RSS records; leave translation caches intact.
const RSS_ABSTRACT_DISPLAY_FIXES = {
  "10.1038/d41586-026-03586-y": "nature",
  "10.1038/d41586-026-03566-2": "nature",
  "10.1038/s41586-026-11248-2": "nature",
  "10.1038/s41586-026-11243-7": "nature",
  "10.1038/s41586-026-11220-0": "nature",
  "10.1038/d41586-026-03538-6": "nature",
  "10.1038/s41564-026-02527-9": "nature",
  "10.1038/s41564-026-02487-0": "nature",
  "10.1038/s41559-026-03215-x": "nature",
  "10.1038/s41467-026-79306-x": "nature",
  "10.1126/science.aen6718": "missing",
  "10.1126/sciadv.aei5129": "missing",
  "10.1073/pnas.2602747123": "pnas",
  "10.1038/s41522-026-01190-6": "nature",
  "10.1038/s41522-026-01189-z": "nature",
  "10.1038/s41522-026-01187-1": "nature",
  "10.1038/s41522-026-01192-4": "nature",
  "10.1038/s41522-026-01184-4": "nature",
  "10.1038/s41522-026-01188-0": "nature",
  "10.1038/s41522-026-01181-7": "nature",
  "10.1038/s41522-026-01177-3": "nature",
  "10.1038/s41579-026-01386-9": "nature",
  "10.1038/s41579-026-01390-z": "nature",
  "10.1038/s41579-026-01383-y": "nature",
  "10.1038/s41579-026-01394-9": "nature",
  "10.1038/s41579-026-01391-y": "nature",
  "10.1038/s41579-026-01392-x": "nature",
  "rss:35b69615db97e651cacf": "missing",
  "rss:9f88c37334afc2b22f67": "missing",
  "10.1038/s42003-026-11189-6": "nature",
  "10.1038/s42003-026-11242-4": "nature",
  "10.1038/s42003-026-11238-0": "nature",
  "10.1038/s41587-026-03358-z": "nature"
};
function displayAbstract(p,lang){
  const value=(lang==='ja'?p.abstract_ja:p.abstract)||'';
  const kind=RSS_ABSTRACT_DISPLAY_FIXES[p.doi]||RSS_ABSTRACT_DISPLAY_FIXES[p.id];
  if(!kind)return value;
  if(kind==='missing')return lang==='ja'?'要旨は取得できていません。':'Abstract unavailable.';
  if(kind==='nature'){
    // Use the known identifier, never a greedy DOI pattern that eats body text.
    const index=value.toLowerCase().indexOf((p.doi||p.id).toLowerCase());
    if(index>=0)return value.slice(index+(p.doi||p.id).length).trim();
    return value.replace(/^(?:Nature(?: Biotechnology| Communications| Ecology & Evolution| Microbiology| Reviews Microbiology)?|Communications Biology|npj Biofilms and Microbiomes)[,、]\s*/, '');
  }
  return value.replace(/^Proceedings of the National Academy of Sciences, Volume \d+, Issue [^.]+\.\s*/, '')
    .replace(/^(?:Proceedings of the National Academy of Sciences|米国科学アカデミー紀要|米国科学アカデミー会報|PNAS)[,、誌\s]*/, '');
}
function paperAbstractHTML(p){return `<section class="abstract ${paperLang==='en'?'en':''}" lang="${paperLang}"><div class="eyebrow">${paperLang==='ja'?'要旨':'ABSTRACT'}</div>${esc(paperLang==='ja'?(displayAbstract(p,'ja')||'日本語訳は準備中'):(displayAbstract(p,'en')||'Abstract unavailable'))}</section>`}
function changePaperLanguage(next){if(!['ja','en'].includes(next))return;const scrollPosition=[window.scrollX||0,window.scrollY||0];paperLang=next;paperLanguageManuallyChosen=true;persist();mountScrollPosition=scrollPosition;if(view==='saved')savedView();else render()}
function optionsFor(p){
  state.optionSets=state.optionSets||{};state.optionVersions=state.optionVersions||{};
  const context=DATA.choice_context,choicePapers=context?.papers||papers;
  const catalog=context?.catalog||observedJournalCatalog(DATA.journal_catalog||[],viewingArchive?[]:(window.PAPER_JOURNALS?.journals||[])),version=optionFingerprint(JSON.stringify([5,mode,state.lap||1,JOURNAL_PROFILES,JOURNAL_ALIASES,catalog,papers.map(a=>[a.answer_journal,a.options])]));
  if(!state.optionSets[p.id]||(!context&&!state.answers[p.id]&&state.optionVersions[p.id]!==version)){
    state.optionSets[p.id]=state.answers[p.id]&&p.options?.length===4?p.options:journalOptions(p,choicePapers,mode,DATA.issue.id+':'+(state.lap||1),catalog);
    state.optionVersions[p.id]=version;persist();
  }
  return state.optionSets[p.id];
}
const allComplete=()=>papers.length>0&&papers.every(p=>state.answers[p.id]?.final!==undefined||state.answers[p.id]?.skipped===true);
function changeMode(next){const scrollPosition=[window.scrollX||0,window.scrollY||0];persist();mode=next;key=stateKey();state=read(key,{batch:0,index:0,screen:'home',answers:{}});selection=null;state.screen='home';persist();mountScrollPosition=scrollPosition;render()}
function toggleSaved(p){const scrollPosition=[window.scrollX||0,window.scrollY||0];if(saved[p.id])delete saved[p.id];else saved[p.id]={id:p.id,title:p.title,title_ja:p.title_ja,journal:p.journal,doi:p.doi};persist();mountScrollPosition=scrollPosition;render()}
const hasProgress=()=>Object.keys(state.answers).length>0||state.batch>0||state.index>0||(state.lap||1)>1||Boolean(state.history?.length);
function restartProgress(){if(!papers.length)return;state={batch:0,index:0,screen:'quiz',answers:{},lap:1,optionSets:{},optionVersions:{}};selection=null;resumeUnanswered()}
function replay(){if(!allComplete())return;state.history=state.history||[];state.history.push({lap:state.lap||1,answers:state.answers});state.answers={};delete state.paperOrder;state.optionSets={};state.optionVersions={};state.batch=0;state.index=0;state.lap=(state.lap||1)+1;state.screen='home';selection=null;persist();render()}
function withTooltip(id,description,button){return `<span class="tooltip-wrap">${button.replace('<button ',`<button aria-describedby="${id}" `)}<span class="tooltip" id="${id}" role="tooltip">${esc(description)}</span><details class="touch-help"><summary>${t('説明を見る','About this option')}</summary><p>${esc(description)}</p></details></span>`}
function bindTooltips(){for(const wrap of app.querySelectorAll('.tooltip-wrap')){const reset=()=>wrap.classList.remove('tooltip-dismissed');wrap.onmouseenter=reset;wrap.onfocusin=reset;wrap.onkeydown=event=>{if(event.key==='Escape')wrap.classList.add('tooltip-dismissed')}}}
function modePicker(){return `<fieldset class="mode-picker"><legend>${t('難易度','Difficulty')}</legend><div class="actions">${['professional','beginner'].map(m=>withTooltip('difficulty-help-'+m,m==='beginner'?t('初心者モード。モードごとに進捗を保存します。','Beginner mode. Progress is saved separately for each mode.'):t('スコープが近い雑誌を優先。IFが登録されている場合は近さも加味します。モードごとに進捗を保存します。','Prioritizes similar journal scopes and, where recorded, similar IF. Progress is saved separately for each mode.'),`<button class="secondary" data-action="mode" data-mode="${m}" aria-pressed="${mode===m}">${m==='beginner'?'Beginner':'Professional'}</button>`)).join('')}</div></fieldset>`}

const isAnswered=p=>state.answers[p.id]?.final!==undefined||state.answers[p.id]?.skipped===true;
function shuffled(rows){const result=[...rows];for(let i=result.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[result[i],result[j]]=[result[j],result[i]]}return result}
function orderedPapers(){
  if(!Array.isArray(state.paperOrder))return papers;
  const known=new Set(state.paperOrder),added=papers.filter(p=>!known.has(p.id));
  if(added.length){state.paperOrder.push(...shuffled(added).map(p=>p.id));persist()}
  const byId=new Map(papers.map(p=>[p.id,p]));
  return state.paperOrder.map(id=>byId.get(id)).filter(Boolean);
}
function initializePaperOrder(){
  if(Array.isArray(state.paperOrder))return;
  // Preserve an existing legacy round before randomizing any future rounds.
  const legacyRound=papers.slice(state.batch*5,state.batch*5+5);
  if(legacyRound.some(p=>state.answers[p.id])&&legacyRound.some(p=>!isAnswered(p))){
    const prefix=papers.slice(0,state.batch*5+5),known=new Set(prefix.map(p=>p.id));
    state.paperOrder=[...prefix,...shuffled(papers.filter(p=>!known.has(p.id)))].map(p=>p.id);
    return;
  }
  const completed=papers.filter(isAnswered),inFlight=papers.filter(p=>!isAnswered(p)&&state.answers[p.id]?.first!==undefined);
  const pending=papers.filter(p=>!isAnswered(p)&&state.answers[p.id]?.first===undefined);
  state.paperOrder=[...completed,...inFlight,...shuffled(pending)].map(p=>p.id);
}
const getBatch=()=>orderedPapers().slice(state.batch*5,state.batch*5+5),current=()=>getBatch()[state.index];
const answer=p=>p.answer_journal??(p.preprint?null:p.journal);
const forecast=p=>!answer(p);
const link=p=>'https://doi.org/'+canonicalDOI(p.doi);
function shareButton(p){return typeof navigator!=='undefined'&&typeof navigator.share==='function'?`<span class="mobile-share"><button type="button" class="secondary" data-action="share" data-id="${esc(p.id)}">${t('共有','Share')}</button><span class="share-status" role="status"></span></span>`:''}
async function sharePaper(p,button){if(!p)return;const status=button.parentElement.querySelector('.share-status');status.textContent='';try{await navigator.share({title:localizedTitle(p).replace(/<[^>]*>/g,''),url:link(p)})}catch(error){if(error.name!=='AbortError')status.textContent=t('共有できませんでした。もう一度お試しください。','Could not share. Please try again.')}}
const tag=x=>uiLang==='ja'?x:({'海洋微生物':'Marine microbiology','微生物ゲノミクス':'Microbial genomics','微生物学':'Microbiology','微生物進化':'Microbial evolution'}[x]||x);
const resultMark=(p,a)=>a.skipped?t('スキップ','Skipped'):forecast(p)?t('採点待ち','Pending'):(a.first===answer(p)?'○':'×')+' → '+(a.final===answer(p)?'○':'×');
function persist(){try{localStorage.setItem(key,JSON.stringify(state));localStorage.setItem('paper-current-mode',JSON.stringify(mode));localStorage.setItem('paper-current-content',JSON.stringify(contentMode));localStorage.setItem('paper-current-saved',JSON.stringify(saved));localStorage.setItem('paper-current-ui-language',JSON.stringify(uiLang))}catch{storageOK=false}}
function mount(html){app.innerHTML=html;document.documentElement.lang=uiLang;document.title=t('Paper Current — 新着論文クイズ','Paper Current — Weekly paper quiz');document.querySelector('#savedBtn').textContent=t('あとで読む','Read later')+' '+Object.keys(saved).length;document.querySelector('#languageBtn').textContent=uiLang==='ja'?'UI: English':'UI: 日本語';document.querySelector('#languageBtn').lang=uiLang==='ja'?'en':'ja';const footerTop=document.querySelector('#footer-top');if(footerTop)footerTop.textContent=t('トップに戻る ↑','Back to top ↑');act('paper-lang',el=>changePaperLanguage(el.dataset.paperLang));act('latest-home',returnToLatest);act('archive-browser',openArchiveBrowser);act('content',el=>changeContent(el.dataset.content));bindTooltips();act('share',el=>sharePaper(papers.find(p=>p.id===el.dataset.id)||saved[el.dataset.id],el));if(mountScrollPosition){window.scrollTo(...mountScrollPosition);mountScrollPosition=null}else window.scrollTo(0,0)}
function act(name,fn){app.querySelectorAll('[data-action="'+name+'"]').forEach(el=>el.onclick=()=>fn(el))}
function changeContent(next){if(!['journals','biorxiv','latest'].includes(next))return;archiveBrowserOpen=false;persist();contentMode=next;papers=selectPapers(DATA);key=stateKey();state=read(key,{batch:0,index:0,screen:'home',answers:{}});state.screen='home';selection=null;persist();render()}
function readingHeading(){const label=weekLabel(DATA.issue.id,DATA.issue.label);return `<div class="reading-context"><div class="eyebrow">${archiveBrowserOpen?t('過去の論文を探す','EXPLORE PAST PAPERS'):viewingArchive?esc(t(label+'の論文を読む','READ PAPERS · '+label)):t('新着論文を読む','READ NEW PAPERS')}</div></div>`}
function returnToLatest(){archiveBrowserOpen=false;try{history.replaceState(null,'',location.pathname)}catch{}switchIssue(INITIAL_DATA,false);latestQuery='';latestTopic='all';latestSource='all';latestSort='date';changeContent('latest')}
function contentPicker(){return `<nav class="primary-navigation" aria-label="${t('主なメニュー','Main navigation')}"><button class="secondary" data-action="content" data-content="latest" aria-pressed="${!archiveBrowserOpen&&contentMode==='latest'}">${t('論文を読む','Read papers')}</button><button class="secondary" data-action="content" data-content="${contentMode==='biorxiv'?'biorxiv':'journals'}" aria-pressed="${!archiveBrowserOpen&&contentMode!=='latest'}">${t('クイズ','Quiz')}</button><button class="secondary" data-action="archive-browser" aria-pressed="${archiveBrowserOpen}">${t('バックナンバー','Back issues')}</button>${viewingArchive?`<button class="quiet" data-action="latest-home">${t('新着論文一覧へ戻る','Back to latest papers')} →</button>`:''}</nav>`}
function quizKindPicker(){return `${!archiveBrowserOpen&&contentMode!=='latest'?`<div class="quiz-kinds" role="group" aria-label="${t('クイズの種類','Quiz type')}">${[['journals',t('雑誌論文 · 4択クイズ','Journal papers · Four choices')],['biorxiv',t('bioRxiv · 自由予測','bioRxiv · Open prediction')]].map(([kind,label])=>withTooltip('content-help-'+kind,kind==='journals'?t('タイトルで予想し、要旨で再予想する4択クイズです。','Predict from the title, then reconsider after the abstract.'):t('タイトルと要旨から掲載先を自由に予測します。正誤採点はありません。','Predict a venue from the title and abstract. No scoring.'),`<button class="secondary" data-action="content" data-content="${kind}" aria-pressed="${contentMode===kind}">${label}</button>`)).join('')}</div>`:''}`}
let latestShowJournals=true,latestSource='all';
function toggleLatestJournals(button){latestShowJournals=!latestShowJournals;button.setAttribute('aria-pressed',String(latestShowJournals));button.textContent=t(latestShowJournals?'掲載誌を隠す':'掲載誌を表示',latestShowJournals?'Hide journals':'Show journals');app.querySelectorAll('[data-journal]').forEach(el=>el.hidden=!latestShowJournals)}
function sourcePicker(){return `<div class="source-picker" role="group" aria-label="${t('論文の種類','Paper type')}">${[['all',t('すべて','All')],['journals',t('雑誌論文','Journal papers')],['biorxiv','bioRxiv']].map(([kind,label])=>`<button class="secondary" data-action="latest-source" data-source="${kind}" aria-pressed="${latestSource===kind}">${label}</button>`).join('')}</div>`}
const latestOpenAbstracts=new Set();
const IMPACT_YEAR=2025;
const impactByJournal=new Map((window.PAPER_JOURNAL_METRICS?.year===IMPACT_YEAR?window.PAPER_JOURNAL_METRICS.journals:[]).filter(m=>Number.isFinite(m.value)&&m.value>=0).map(m=>[journalKey(m.name),m]));
function paperImpact(p){return p.preprint?null:impactByJournal.get(journalKey(p.journal||p.answer_journal))||null}
function paperImpactHTML(p){if(p.preprint)return '';const name=p.journal||p.answer_journal,metric=paperImpact(p);if(metric?.value!==undefined)return ` <a class="latest-if" href="${esc(metric.source)}" target="_blank" rel="noopener" aria-label="${esc(name)} · ${IMPACT_YEAR} JIF ${metric.value.toFixed(1)} · ${t('出典','Source')}">${IMPACT_YEAR} IF ${metric.value.toFixed(1)} ↗</a>`;const missing=(window.PAPER_JOURNAL_METRICS?.unavailable||[]).find(m=>journalKey(m.name)===journalKey(name));if(missing)return ` <a class="latest-if" href="${esc(missing.source)}" target="_blank" rel="noopener">${missing.status==='new_journal'?t('新しい雑誌 · JIF未付与','New journal · no JIF yet'):t('JIF未付与','No JIF assigned')} ↗</a>`;return name?` <a class="latest-if" href="https://absnexora.com/journal-rankings/jcr/" target="_blank" rel="noopener">${t('JIFを確認','Check JIF')} ↗</a>`:''}
let latestQuery='',latestSort='date',latestTotal=0,latestTopic='all';
const TOPIC_RULES={marine:/\b(marine|ocean\w*|seawater|coastal|estuar\w*|aquatic|freshwater|plankton\w*)\b|海洋|海水|沿岸|深海|水圏|淡水|プランクトン/i,ecology:/\b(ecolog\w*|microbiome\w*|microbiota|communit\w*|symbio\w*|biogeochem\w*)\b|生態|微生物群集|微生物叢|共生|物質循環/i,genomics:/\b(genom\w*|metagenom\w*|transcriptom\w*|pangenom\w*|sequencing)\b|ゲノム|メタゲノム|トランスクリプトーム|シーケン/i};
function matchesTopic(p,topic){return topic==='all'||Boolean(TOPIC_RULES[topic]?.test([p.title,p.title_ja,p.abstract,p.abstract_ja,...(p.tags||[])].join(' ')))}
function searchText(value){return String(value||'').replace(/<[^>]*>/g,' ').normalize('NFKC').toLocaleLowerCase().replace(/\s+/g,' ').trim()}
function latestRows(){
  const terms=searchText(latestQuery).split(' ').filter(Boolean);
  const collator=new Intl.Collator(paperLang,{numeric:true,sensitivity:'base'});
  const today=new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'}),cutoff=new Date(Date.parse(today+'T00:00:00+09:00')-6*86400000).toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'});
  const candidates=papers.filter(p=>viewingArchive||!Array.isArray(window.PAPER_RECENT_DATA)||String(p.collected_date||p.date||'')>=cutoff);latestTotal=candidates.length;
  const rows=candidates.map((p,index)=>({p,index,title:latestSort==='title'?searchText(paperLang==='ja'?(p.title_ja||p.title):p.title):''})).filter(({p})=>{
    if(latestSource==='journals'&&p.preprint||latestSource==='biorxiv'&&!p.preprint)return false;
    if(!matchesTopic(p,latestTopic))return false;
    if(!terms.length)return true;
    const text=searchText([p.title,p.title_ja,p.abstract,p.abstract_ja,p.doi].join(' '));
    return terms.every(term=>text.includes(term));
  });
  const publicationTime=p=>{const time=Date.parse(p.date||'');return Number.isFinite(time)?time:-Infinity};
  rows.sort((a,b)=>{
    if(latestSort==='if')return ((paperImpact(b.p)?.value??-Infinity)-(paperImpact(a.p)?.value??-Infinity))||b.index-a.index;
    if(latestSort==='date')return (publicationTime(b.p)-publicationTime(a.p))||b.index-a.index;
    if(latestSort==='title')return collator.compare(a.title,b.title)||b.index-a.index;
    return b.index-a.index;
  });
  return rows.map(({p})=>p);
}
function latestCardsHTML(rows){return rows.map((p,i)=>`<article class="latest-card"><div class="latest-card-top"><span class="latest-number">${String(i+1).padStart(2,'0')}</span><span class="latest-journal" data-journal${latestShowJournals?'':' hidden'}>${esc(p.preprint?t('bioRxiv · プレプリント','bioRxiv · Preprint'):(p.journal||p.published_journal||t('掲載先未確定','Journal pending')))}${paperImpactHTML(p)}</span>${p.date?`<time class="latest-date" datetime="${esc(p.date)}">${esc(p.date)}</time>`:''}</div><h2 class="latest-title" lang="${paperLang}">${titleHTML(localizedTitle(p))}</h2><details class="latest-abstract" data-abstract-id="${esc(p.id)}"${latestOpenAbstracts.has(p.id)?' open':''}><summary>${latestOpenAbstracts.has(p.id)?t('要旨を閉じる','Close abstract'):t('要旨を読む','Read abstract')}</summary>${paperAbstractHTML(p)}</details><div class="latest-card-actions"><button class="quiet" data-action="latest-save" data-id="${esc(p.id)}" aria-pressed="${Boolean(saved[p.id])}">${saved[p.id]?t('保存済み ✓','Saved ✓'):t('あとで読む ＋','Read later ＋')}</button><a href="${esc(link(p))}" target="_blank" rel="noopener">${t('原文を読む','Read paper')} ↗</a>${shareButton(p)}</div></article>`).join('')||`<p class="notice">${latestQuery?t('一致する論文がありません。検索語を変えてみてください。','No matching papers. Try different search terms.'):latestTotal?t('一致する論文がありません。','No matching papers.'):t('直近7日間に収録された論文はありません。年・月から過去問を選べます。','No papers were collected in the last seven days. Choose an archive by year and month.')}</p>`}
function latestResultCount(rows){return t(rows.length+' / '+latestTotal+'本',rows.length+' / '+latestTotal+' papers')}
function bindLatestCards(){
  act('latest-save',el=>{const p=papers.find(p=>p.id===el.dataset.id);if(p)toggleSaved(p)});
  act('share',el=>sharePaper(papers.find(p=>p.id===el.dataset.id),el));
  app.querySelectorAll('[data-abstract-id]').forEach(el=>el.ontoggle=()=>{if(el.open)latestOpenAbstracts.add(el.dataset.abstractId);else latestOpenAbstracts.delete(el.dataset.abstractId);el.querySelector('summary').textContent=el.open?t('要旨を閉じる','Close abstract'):t('要旨を読む','Read abstract')});
}
function updateLatestResults(){
  const rows=latestRows();document.querySelector('#latest-results').innerHTML=latestCardsHTML(rows);
  document.querySelector('#latest-result-count').textContent=latestResultCount(rows);
  document.querySelector('#latest-heading-count').textContent=t(rows.length+'本',rows.length+' papers');
  document.querySelector('#latest-metrics-help').hidden=latestSort!=='if';bindLatestCards();
}
function latestView(){
  const rows=latestRows();
  mount(`${contentPicker()}<div class="page-heading latest-heading"><h1>${t(viewingArchive?'この週の論文':'新着論文',viewingArchive?'This week’s papers':'Latest papers')} <span id="latest-heading-count">${t(rows.length+'本',rows.length+' papers')}</span></h1>${viewingArchive?`<span class="hint">${esc(weekLabel(DATA.issue.id,DATA.issue.label))}</span>`:''}</div><div class="latest-meta">${updateNotice()}</div><div class="reading-settings">${sourcePicker()}<button type="button" class="quiet" data-action="latest-journals" aria-pressed="${latestShowJournals}">${t(latestShowJournals?'掲載誌を隠す':'掲載誌を表示',latestShowJournals?'Hide journals':'Show journals')}</button></div><div class="latest-controls"><label class="latest-search">${t('論文を検索','Search papers')}<input id="latest-search" type="search" value="${esc(latestQuery)}" placeholder="${t('タイトル・要旨を日本語／英語で検索','Search titles and abstracts in Japanese or English')}" aria-describedby="latest-search-help" autocomplete="off"></label><label class="latest-sort">${t('並び替え','Sort by')}<select id="latest-sort">${[['added',t('サイト追加順 · 新しい順','Recently added')],['date',t('論文公開日 · 新しい順','Publication date · Newest')],['title',t('タイトル順','Title')],['if',t('IF順（2025）· 高い順','Journal IF (2025) · Highest')]].map(([value,label])=>`<option value="${value}"${latestSort===value?' selected':''}>${label}</option>`).join('')}</select></label><label class="latest-topic">${t('分野','Topic')}<select id="latest-topic">${[['all',t('すべて','All topics')],['marine',t('海洋・水圏','Marine & aquatic')],['ecology',t('微生物生態','Microbial ecology')],['genomics',t('ゲノミクス','Genomics')]].map(([value,label])=>`<option value="${value}"${latestTopic===value?' selected':''}>${label}</option>`).join('')}</select></label><p class="hint topic-help">${t('分野は日英のタイトル・要旨・タグのキーワードで分類しています。複数分野に該当する場合があり、網羅性は保証されません。','Topics use keywords in titles, abstracts and tags in both languages. Topics can overlap and may miss relevant papers.')}</p><p id="latest-search-help" class="hint">${t('表示言語に関係なく日英両方を検索。スペースで区切ると、すべての語を含む論文に絞れます。','Search both languages. Separate words with spaces to match all terms.')}</p><p id="latest-result-count" class="hint" role="status">${latestResultCount(rows)}</p></div><p id="latest-metrics-help" class="hint"${latestSort==='if'?'':' hidden'}>${t('2025年JIFの高い順。未確認・対象外は末尾に表示します。掲載誌とともにIFと出典を表示します。','Highest 2025 JIF first; unverified or inapplicable values come last. Values and sources appear beside each journal.')}</p><div id="latest-results" class="latest-list">${latestCardsHTML(rows)}</div><div class="latest-floating">${paperLanguagePicker()}${viewingArchive?`<button type="button" class="secondary" data-action="latest-home">${t('新着論文一覧へ戻る','Back to latest papers')} →</button>`:''}<button type="button" class="secondary latest-top-button" data-action="latest-top" aria-label="${t('ページの先頭へ','Back to top')}" title="${t('ページの先頭へ','Back to top')}"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 19V5m-6 6 6-6 6 6"/></svg></button></div><p class="hint">${t('日本語訳はPLaMoによる機械翻訳です。','Japanese translations are generated by PLaMo.')}</p>`);
  act('content',el=>changeContent(el.dataset.content));
  act('latest-journals',toggleLatestJournals);
  act('latest-source',el=>{if(!['all','journals','biorxiv'].includes(el.dataset.source))return;latestSource=el.dataset.source;app.querySelectorAll('[data-action="latest-source"]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.source===latestSource)));updateLatestResults()});
  document.querySelector('#latest-topic').onchange=event=>{if(event.target.value!=='all'&&!TOPIC_RULES[event.target.value])return;latestTopic=event.target.value;updateLatestResults()};
  act('latest-top',()=>window.scrollTo({top:0,left:0,behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'}));
  bindLatestCards();
  document.querySelector('#latest-search').oninput=event=>{latestQuery=event.target.value;updateLatestResults()};
  document.querySelector('#latest-sort').onchange=event=>{if(!['added','date','title','if'].includes(event.target.value))return;latestSort=event.target.value;updateLatestResults()};
  renderArchivePanel();
}

function resumeUnanswered(){initializePaperOrder();const index=orderedPapers().findIndex(p=>!isAnswered(p));if(index<0)return;state.batch=Math.floor(index/5);state.index=index%5;state.screen='quiz';selection=null;persist();render()}
function weekLabel(id,fallback){const m=/^(\d{4})-W(\d{2})$/.exec(id||'');if(!m)return fallback||id||'';const jan4=new Date(Date.UTC(+m[1],0,4)),start=new Date(+jan4-((jan4.getUTCDay()+6)%7)*86400000+(+m[2]-1)*7*86400000),end=new Date(+start+6*86400000);return `${start.getUTCFullYear()}/${start.getUTCMonth()+1}/${start.getUTCDate()}–${end.getUTCMonth()+1}/${end.getUTCDate()} (${id})`}
function formatUpdated(value){const d=new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(value)?value:value+'+09:00');if(!Number.isFinite(+d))return '';return new Intl.DateTimeFormat(uiLang==='ja'?'ja-JP':'en-GB',{timeZone:'Asia/Tokyo',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).format(d)}
function updateNotice(){if(!DATA.issue.updated_at)return '';const day=new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'}),count=DATA.issue.added_date===day?papers.filter(p=>(DATA.issue.added_ids||[]).includes(p.id)).length:0;return `<p class="hint">${t('最終更新','Updated')}: ${esc(formatUpdated(DATA.issue.updated_at))} JST · ${t('本日追加 '+count+'本',count+' added today')}</p>`}
function home(){if(contentMode==='latest')return latestView();const bio=contentMode==='biorxiv';mount(`${contentPicker()}<div class="hero"><div class="page-heading"><h1>${bio?t('次の掲載先を<br class="mobile-break">予測してみよう','Where might this<br class="mobile-break"> paper be published?'):t('どの雑誌に<br class="mobile-break">掲載された？','Which journal<br class="mobile-break"> published this?')}</h1>${viewingArchive?readingHeading():''}</div><p class="lead">${bio?t('bioRxivのタイトルと要旨を同時に読んで、掲載先を自由に考えてみてください。','Read the bioRxiv title and abstract together, and consider a possible publication venue.'):t('タイトルと要旨から掲載誌を予想する、1回5問の4択クイズ。','Guess the journal from the title and abstract in a five-question, multiple-choice quiz.')}</p><div class="quiz-setup">${quizKindPicker()}${bio?'':modePicker()}<div class="actions">${!papers.length?`<p class="notice">${t('この号には準備できた論文がまだありません。収集・翻訳後に追加されます。','No papers are ready in this section yet. Papers appear after collection and translation.')}</p>`:allComplete()?`<button class="primary" data-action="replay">${t((state.lap||1)+1+'周目へ →','Start pass '+((state.lap||1)+1)+' →')}</button>`:`<button class="primary" data-action="start">${Object.keys(state.answers).length?t('続きから','Continue'):bio?t('読み始める','Start reading'):t(Math.min(5,papers.length)+'問に挑戦','Start '+Math.min(5,papers.length)+' questions')} →</button>`}${papers.length&&hasProgress()?withTooltip('restart-help',t('現在のモードの回答・進捗をリセットします。「あとで読む」は残ります。','Starting over resets answers and progress for this mode. Saved papers are kept.'),`<button class="quiet restart-button" data-action="restart">${t('最初からやり直す','Start over')}</button>`):''}</div></div></div>${updateNotice()}<div class="notice">${isDemo?t('体験用データです。訳文は試作用です。','Demo data with draft translations.'):t('日本語訳はPLaMoによる機械翻訳です。','Japanese translations are generated by PLaMo.')} ${papers.length}${t('本収録。',' papers available.')} ${bio?t('自由予測では選択肢・正誤採点はありません。','Open predictions have no choices or scoring.'):t('雑誌掲載論文だけを出題します。','Only journal-published papers are included.')}</div>${!storageOK?'<p>'+t('このブラウザでは履歴を保存できません。','This browser cannot save progress.')+'</p>':''}`);act('content',el=>changeContent(el.dataset.content));act('mode',el=>changeMode(el.dataset.mode));act('replay',replay);act('restart',restartProgress);act('start',()=>{if(!papers.length)return;return resumeUnanswered()});renderArchivePanel()}
function advancePreprint(){const p=current();if(!p)return;state.answers[p.id]={final:'read'};state.index++;normalize();persist();render()}
function preprintView(){const p=current();if(!p)return preprintSummary();mount(`<div class="quiztop"><span>bioRxiv · ${state.lap||1}${t('周目',' pass')} · ${state.index+1} / ${getBatch().length}</span><button class="quiet" data-action="home">${t('中断してホームへ','Pause / Home')}</button></div><div class="progress"><div style="width:${state.index/getBatch().length*100}%"></div></div><article class="paper"><div class="tag">${esc((p.tags||[]).map(tag).join(' / '))}</div>${paperLanguagePicker()}${paperTitleHTML(p)}${paperAbstractHTML(p)}</article><div class="notice"><h2>${t('掲載先を予測してみてください。','Consider where this paper might be published.')}</h2><p>${t('タイトルと要旨から、どの雑誌が合いそうか考えてみましょう。','Which journal seems suitable for this title and abstract?')}</p></div><div class="actions"><button class="primary" data-action="read-next">${state.index+1===getBatch().length?t('今回の読了一覧へ','View reading summary'):t('次の論文へ →','Next paper →')}</button><button class="secondary" data-action="save">${saved[p.id]?t('保存済み ✓','Saved ✓'):t('あとで読む ＋','Read later ＋')}</button>${shareButton(p)}<a class="quiet" href="${esc(link(p))}" target="_blank" rel="noopener">${t('原文を読む','Read preprint')} ↗</a></div>`);act('home',goHome);act('read-next',advancePreprint);act('save',()=>toggleSaved(p))}
function preprintSummary(){const remaining=papers.filter(p=>!isAnswered(p)).length;mount(`<div class="eyebrow">bioRxiv</div><h1>${getBatch().length}${t('本読了',' papers read')}</h1><div class="actions">${remaining?`<button class="primary" data-action="more">${t('次の'+Math.min(5,remaining)+'本へ →','Read '+Math.min(5,remaining)+' more →')}</button>`:allComplete()?`<button class="primary" data-action="replay">${t((state.lap||1)+1+'周目へ →','Start pass '+((state.lap||1)+1)+' →')}</button>`:''}<button class="secondary" data-action="saved">${t('保存した論文','Saved papers')}</button><button class="quiet" data-action="home">${t('ホームへ','Home')}</button></div>${getBatch().map(p=>`<div class="review"><h3 lang="${paperLang}">${titleHTML(localizedTitle(p))}</h3><a href="${esc(link(p))}" target="_blank" rel="noopener">${t('原文','Preprint')} ↗</a></div>`).join('')}`);act('more',resumeUnanswered);act('replay',replay);act('saved',savedView);act('home',goHome)}

function skipPaper(){const p=current();if(contentMode!=='journals'||!p)return;const answerState=state.answers[p.id]||{};if(answerState.first!==undefined||answerState.final!==undefined||answerState.skipped)return;state.answers[p.id]={skipped:true};state.index++;selection=null;normalize();persist();render()}
function normalize(){if(!getBatch().length){state.batch=0;state.index=0}while(state.index<getBatch().length&&isAnswered(getBatch()[state.index]))state.index++;if(state.index>=getBatch().length)state.screen='summary'}
function quiz(){if(contentMode==='biorxiv')return preprintView();const p=current();if(!p)return summary();const options=optionsFor(p);const a=state.answers[p.id]||{},stage=a.final!==undefined?'result':a.first!==undefined?'abstract':'title',result=stage==='result',pending=forecast(p),correct=answer(p);selection=selection??(stage==='abstract'?a.first:null);
mount(`<div class="quiztop"><span>${esc(DATA.issue.id)} · ${mode==='beginner'?'Beginner':'Professional'} · ${state.lap||1}${t('周目',' pass')} · ${state.batch?t('追加ラウンド ','Extra round ')+state.batch:t('最初のラウンド','First round')}</span><button class="quiet" data-action="home">${t('中断してホームへ','Pause / Home')}</button></div><div class="progress"><div style="width:${(state.index+(result?1:0))/getBatch().length*100}%"></div></div><div class="steps"><span class="${stage==='title'?'active':''}">01 ${t('タイトル','Title')}</span><span class="${stage==='abstract'?'active':''}">02 ${t('要旨','Abstract')}</span><span class="${result?'active':''}">03 ${t('結果','Result')}</span><span style="margin-left:auto">${state.index+1} / ${getBatch().length}</span></div>${result?`<div class="result-banner"><span class="eyebrow" style="color:#bfd5cb">${pending?t('予想を記録しました','FORECAST RECORDED'):t('実際の掲載誌','PUBLICATION VENUE')}</span><h2>${esc(pending?t('bioRxiv · 掲載先未確定','bioRxiv · Journal pending'):correct)}</h2><p>${pending?t('掲載先が確定していないため、正誤は採点しません。','No journal is confirmed. This prediction is not scored.'):(a.final===correct?t('正解！','Correct!'):t('予想と異なる掲載先でした。','A different venue than you predicted.'))}</p><p>${t('タイトル時点','Title')}: ${esc(a.first)} → ${t('要旨後','Abstract')}: ${esc(a.final)}</p></div>`:''}<div class="quizgrid">${result?`<details class="paper result-paper"><summary>${t('タイトル・要旨を読む','Read title and abstract')}</summary><div class="result-paper-content">`:'<article class="paper">'}<div class="tag">${esc((p.tags||[]).map(tag).join(' / '))}${p.review?' · Review':''}</div>${paperLanguagePicker()}${paperTitleHTML(p)}${stage!=='title'?`${paperAbstractHTML(p)}`:'<p class="hint" style="margin-top:30px">'+t('まずはタイトルだけで予想してください。','Make your first prediction using only the title.')+'</p>'}${result?`<div class="meta">${esc(p.authors)}<br>${esc(p.date)} · DOI: ${esc(p.doi)}<br><a href="${esc(p.source_url)}" target="_blank" rel="noopener">${t('取得元','Source')}</a> · <a href="${esc(p.license_url)}" target="_blank" rel="noopener">${esc(p.license)}</a><br>${t('日本語訳','Japanese translation')}: ${esc(p.translation_label||t('未作成','Not available'))}${p.preprint?'<br>'+t('本文はプレプリント版。査読済みとは限りません。','Text is from a preprint; peer review is not implied.'):''}</div>`:''}${result?'</div></details>':'</article>'}<aside><div class="eyebrow">${result?t('あなたの予想','YOUR PREDICTION'):stage==='title'?t('最初の予想','FIRST GUESS'):t('2回目の予想','SECOND GUESS')}</div><h3>${result?t('予想を振り返る','Review your prediction'):stage==='title'?t('どの雑誌に掲載されそう？','Which journal would publish this?'):t('読んだあと、予想は変わる？','Would you change your prediction?')}</h3><div class="choices">${options.map((o,i)=>`<button class="choice ${!result&&selection===o?'selected':''} ${result&&!pending&&o===correct?'correct':''} ${result&&!pending&&o===a.final&&o!==correct?'wrong':''} ${result&&pending&&o===a.final?'selected':''}" data-action="choice" aria-pressed="${(result?a.final:selection)===o}" data-option="${i}" ${result?'disabled':''}><span class="letter">${'ABCD'[i]}</span><span>${esc(o)}${result&&!pending&&o===correct?' ✓':''}</span></button>`).join('')}</div>${result?`<div class="actions"><a class="primary" style="text-decoration:none" href="${esc(link(p))}" target="_blank" rel="noopener">${t('原著を読む','Read paper')} ↗</a><button class="secondary" data-action="save">${saved[p.id]?t('保存済み ✓','Saved ✓'):t('あとで読む ＋','Read later ＋')}</button>${shareButton(p)}</div><button class="primary full" data-action="next">${state.index+1===getBatch().length?t('今回の結果を見る','View round results'):t('次の論文へ →','Next paper →')}</button>`:`<button class="primary full" data-action="confirm" ${selection===null?'disabled':''}>${stage==='title'?t('確定して要旨へ →','Confirm / Read abstract →'):t('確定して結果を見る →','Confirm / View result →')}</button><p class="hint">${stage==='abstract'?t('最初の予想：','First prediction: ')+esc(a.first)+t('。そのまま確定することもできます。','. You can keep this choice.'):t('回答は次の段階で変更できます。','You can change your answer in the next stage.')}</p>${stage==='title'?`<button class="quiet full" data-action="skip">${t('この論文をスキップ','Skip this paper')}</button>`:''}`}</aside></div>`);
act('home',goHome);act('skip',skipPaper);act('choice',el=>{selection=options[Number(el.dataset.option)];app.querySelectorAll('[data-action="choice"]').forEach(button=>{const selected=button===el;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected))});app.querySelectorAll('[data-action="confirm"]').forEach(button=>button.disabled=false)});act('confirm',()=>{if(selection===null)return;if(stage==='title')state.answers[p.id]={first:selection};else state.answers[p.id].final=selection;selection=null;persist();render()});act('save',()=>toggleSaved(p));act('next',()=>{state.index++;selection=null;normalize();persist();render()})}
function summary(){if(contentMode==='biorxiv')return preprintSummary();const complete=getBatch().filter(p=>state.answers[p.id]?.final!==undefined||state.answers[p.id]?.skipped),scored=complete.filter(p=>!state.answers[p.id].skipped&&!forecast(p)),skipped=complete.filter(p=>state.answers[p.id].skipped).length,pendingCount=complete.filter(p=>!state.answers[p.id].skipped&&forecast(p)).length,n=scored.length,first=scored.filter(p=>state.answers[p.id].first===answer(p)).length,final=scored.filter(p=>state.answers[p.id].final===answer(p)).length,remaining=papers.filter(p=>!isAnswered(p)).length;
mount(`<div class="eyebrow">${t('今回の結果','ROUND COMPLETE')}</div><h1>${complete.length}${t('問完了',' papers completed')}</h1><p class="muted">${t('採点対象は掲載先が確定した論文のみです。未出版の予想：','Only confirmed publication venues are scored. Pending forecasts: ')}${pendingCount} · ${t('スキップ：','Skipped: ')}${skipped}</p><div class="scoregrid"><div class="score">${t('タイトルの予想','Title prediction')}<strong>${first}<small style="font-size:20px"> / ${n}</small></strong></div><div class="score">${t('要旨後','After the abstract')}<strong>${final}<small style="font-size:20px"> / ${n}</small></strong></div></div><div class="actions">${remaining>0?`<button class="primary" data-action="more">${remaining>=5?t('もう5問に挑戦 →','Try five more →'):t('残り'+remaining+'問に挑戦 →','Try the remaining '+remaining+' →')}</button>`:'<span class="badge">'+t('この号の問題をすべて完了しました','All papers in this issue completed')+'</span>'+(allComplete()?`<button class="primary" data-action="replay">${t((state.lap||1)+1+'周目へ →','Start pass '+((state.lap||1)+1)+' →')}</button>`:'')}<button class="secondary" data-action="saved">${t('保存した論文を見る','Saved papers')}</button><button class="quiet" data-action="home">${t('ホームへ','Home')}</button></div><p class="hint">${t('追加ラウンドの成績は、最初のラウンドと分けて記録します。','Extra rounds are scored separately from the first five.')}</p><div class="sectionhead"><span class="eyebrow">${t('回答一覧','YOUR ANSWERS')}</span></div>${complete.map(p=>`<div class="review"><span class="badge">${resultMark(p,state.answers[p.id])}</span><h3 lang="${paperLang}">${titleHTML(localizedTitle(p))}</h3><p>${esc(state.answers[p.id].skipped?t('スキップした論文','Skipped paper'):(answer(p)||t('bioRxiv · 掲載先未確定','bioRxiv · Journal pending')))} · <a href="${esc(link(p))}" target="_blank" rel="noopener">${t('原著','Paper')} ↗</a></p></div>`).join('')}`);act('replay',replay);act('more',resumeUnanswered);act('saved',savedView);act('home',goHome)}
let view='quiz';
function readingListCSV(rows){
  const cell=value=>{let text=String(value??'');if(/^\s*[=+\-@]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"'};
  const records=[['id','title','title_ja','journal','doi','url'],...rows.map(p=>[p.id,p.title,p.title_ja,p.journal,p.doi,canonicalDOI(p.doi)?link(p):''])];
  return '\uFEFF'+records.map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';
}
function downloadReadingList(format){
  const rows=Object.values(saved),csv=format==='csv',content=csv?readingListCSV(rows):JSON.stringify(rows,null,2);
  const url=URL.createObjectURL(new Blob([content],{type:csv?'text/csv;charset=utf-8':'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='paper-current-reading-list.'+(csv?'csv':'json');a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function savedView(){view='saved';mount(`<div class="eyebrow">${t('保存した論文','SAVED PAPERS')}</div><h1>${t('あとで読む','Read later')}</h1><p class="muted">${t('このブラウザに保存された論文です。','Papers saved in this browser.')}</p><div class="actions"><button class="secondary" data-action="back">${contentMode==='latest'?t('論文一覧に戻る','Back to papers'):t('クイズに戻る','Back to quiz')}</button><button class="quiet" data-action="export">${t('一覧をJSONで保存','Export JSON')}</button><button class="quiet" data-action="export-csv">${t('一覧をCSVで保存','Export CSV')}</button></div>${Object.values(saved).map(p=>`<div class="saved-item"><h3 lang="${paperLang}">${titleHTML(localizedTitle(p))}</h3><span class="badge">${esc(p.journal)}</span> <a href="${esc(link(p))}" target="_blank" rel="noopener">${t('原著を読む','Read paper')} ↗</a>${shareButton(p)}<button class="quiet" data-action="remove" data-id="${esc(p.id)}">${t('保存を解除','Remove')}</button></div>`).join('')||'<p style="margin-top:40px">'+t('保存した論文はありません。','No saved papers yet.')+'</p>'}`);act('back',render);act('remove',el=>{delete saved[el.dataset.id];persist();savedView()});act('export',()=>downloadReadingList('json'));act('export-csv',()=>downloadReadingList('csv'))}
function openArchiveBrowser(){persist();archiveBrowserOpen=true;state.screen='home';render()}
function archiveBrowserView(){view='archives';mount(`${contentPicker()}<div class="page-heading"><h1>${t('バックナンバー','Back issues')}</h1></div><section id="archive-panel"></section>`);renderArchivePanel()}
function render(){view='quiz';if(archiveBrowserOpen)return archiveBrowserView();if(contentMode==='latest')return latestView();if(state.screen==='summary')summary();else if(state.screen==='quiz')quiz();else home()}
function switchIssue(data,archived){
  persist();DATA=data;viewingArchive=archived;papers=selectPapers(data);
  key=stateKey();state=read(key,{batch:0,index:0,screen:'home',answers:{}});
  isDemo=DATA.papers.some(p=>p.demo)||DATA.issue.id.startsWith('prototype');selection=null;
}
function goHome(){try{history.replaceState(null,'',location.pathname)}catch{}state.screen='home';persist();if(viewingArchive)switchIssue(INITIAL_DATA,false);state.screen='home';persist();render()}
function archivedEntries(){
  if(!archiveIndex)return [];
  const days=archiveIndex.archive_after_days??90,cutoff=Date.now()-days*86400000;
  return archiveIndex.issues.filter(i=>{if(archiveIndex.archive_policy==='weekly'){if(i.archive_available_at)return Date.parse(i.archive_available_at)<=Date.now();if(i.week_ends_at)return Date.parse(i.week_ends_at)<=Date.now();const m=/^(\d{4})-W(\d{2})$/.exec(i.id);if(m){const jan4=new Date(Date.UTC(Number(m[1]),0,4)),monday=jan4.getTime()-((jan4.getUTCDay()+6)%7)*86400000;return monday+Number(m[2])*7*86400000-9*3600000<=Date.now()}return i.id!==INITIAL_DATA.issue.id&&Date.parse(i.date+'T00:00:00Z')<Date.now()}return Date.parse(i.date+'T00:00:00Z')<=cutoff}).sort((a,b)=>b.date.localeCompare(a.date));
}
async function loadArchiveIndex(){
  if(archiveLoading)return;archiveLoading=true;
  try{const r=await fetch('data/archive-index.json',{cache:'no-cache'});if(!r.ok)throw Error('HTTP '+r.status);archiveIndex=await r.json();archiveError=false}
  catch{archiveError=true}finally{archiveLoading=false;if(view==='archives')renderArchivePanel()}
}
function renderArchivePanel(){
  const panel=document.querySelector('#archive-panel');if(!panel)return;
  const entries=archivedEntries(),years=[...new Set(entries.map(i=>String(i.year)))];
  panel.innerHTML=`<div class="sectionhead"><h2>${t('過去の週を選ぶ','Choose a past week')}</h2><span class="badge">${archiveIndex?.archive_policy==='weekly'?t('7日経過後に公開','Available after seven days'):(archiveIndex?.archive_after_days??90)+t('日経過後',' days after release')}</span></div><p class="muted">${t('年と月から週を選ぶと、論文一覧・雑誌論文クイズ・bioRxivを切り替えて読めます。','Choose a year, month and week, then browse its papers, journal quiz or bioRxiv.')}</p>${archiveError?'<p class="hint">'+t('バックナンバーの取得に失敗しました。GitHub Pages上で再試行してください。','Could not load back issues. Try again on GitHub Pages.')+'</p><button class="secondary" data-action="retry-index">'+t('再試行','Retry')+'</button>':!archiveIndex?'<p>'+t('バックナンバーを読み込み中…','Loading back issues…')+'</p>':!entries.length?'<p class="hint">'+t('公開対象のバックナンバーはまだありません。','No back issues are available yet.')+'</p>':`<div class="archive-filters"><label>${t('年','Year')}<select id="archive-year">${years.map(y=>'<option>'+esc(y)+'</option>').join('')}</select></label><label>${t('月','Month')}<select id="archive-month"></select></label></div><div id="archive-issues"></div>`}`;
  act('retry-index',loadArchiveIndex);
  if(entries.length){const year=document.querySelector('#archive-year'),month=document.querySelector('#archive-month');
    const updateMonth=()=>{const months=[...new Set(entries.filter(i=>String(i.year)===year.value).map(i=>i.month))];month.innerHTML=months.map(m=>'<option value="'+m+'">'+m+'</option>').join('');updateIssues()};
    const updateIssues=()=>{document.querySelector('#archive-issues').innerHTML=entries.filter(i=>String(i.year)===year.value&&String(i.month)===month.value).map(i=>`<div class="archive-row"><span><b>${esc(weekLabel(i.id,i.date))}</b><br><small>${esc(i.date)} · ${i.count}${t('本',' papers')}</small></span><button class="secondary" data-action="archive-open" data-id="${esc(i.id)}">${t('この週の論文を見る','View this week’s papers')} →</button></div>`).join('');act('archive-open',el=>openArchive(el.dataset.id))};
    year.onchange=updateMonth;month.onchange=updateIssues;updateMonth();
  }
  if(!archiveIndex&&!archiveLoading&&!archiveError)loadArchiveIndex();
}
async function openArchive(id){
  const entry=archiveIndex?.issues.find(i=>i.id===id);if(!entry)return;
  if(!/^data\/issues\/[a-zA-Z0-9_-]+\.json$/.test(entry.path))return;
  const panel=document.querySelector('#archive-panel');
  try{const r=await fetch(entry.path);if(!r.ok)throw Error('HTTP '+r.status);const data=await r.json();if(!Array.isArray(data.papers)||data.issue?.id!==id)throw Error('Invalid archive');contentMode='latest';switchIssue(data,true);archiveBrowserOpen=false;latestQuery='';latestTopic='all';latestSource='all';latestSource='all';try{history.replaceState(null,'','?issue='+encodeURIComponent(id))}catch{}state.screen='home';persist();render();return true}
  catch{if(panel){const p=document.createElement('p');p.className='hint';p.textContent=t('この回を読み込めませんでした。もう一度お試しください。','Unable to load this issue. Please try again.');panel.appendChild(p)}return false}
}
function changeUILanguage(next){if(!['ja','en'].includes(next))return;uiLang=next;if(!paperLanguageManuallyChosen)paperLang=uiLang;persist();if(view==='saved')savedView();else render()}
document.querySelector('#savedBtn').onclick=savedView;document.querySelector('#languageBtn').onclick=()=>changeUILanguage(uiLang==='ja'?'en':'ja');
(async()=>{const requested=new URLSearchParams(location.search).get('issue');if(requested){await loadArchiveIndex();if(archivedEntries().some(i=>i.id===requested)&&await openArchive(requested))return}render()})();
