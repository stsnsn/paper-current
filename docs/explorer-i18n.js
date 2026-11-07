/* Translate interface nodes only. Scientific text and user input remain untouched. */
(function(root){
'use strict';
const dictionary=new Map(Object.entries({
'全体検索・解析':'Search & explore','新着論文を読む':'Read latest papers','新着論文クイズ':'Latest paper quiz','バックナンバー':'Back issues','索引を確認中':'Loading index',
'新着とアーカイブをまとめて検索。検索した文献群から、研究の話題を探索できます。':'Search recent and archived papers, then explore topics in your results.',
'キーワード':'Keywords','検索語':'Search terms','期間':'Period','公開期間':'Publication period','取り込み期間':'Collection period','すべての期間':'All dates','日付を指定…':'Custom date range…','詳細条件':'More filters','日付の基準':'Date basis','開始日・終了日のどちらか一方だけでも指定できます。':'You can specify a start date, an end date, or both.','SAR11、Pelagibacter、dissolved organic matter…':'SAR11, Pelagibacter, dissolved organic matter…',
'日英のタイトル・要旨・DOIを検索。空白で区切るとすべての語に一致。':'Search titles, abstracts and DOIs in English and Japanese. Separate words to match all terms.',
'年':'Year','すべての年':'All years','期間の基準':'Date basis','論文公開日':'Publication date','サイト取り込み日':'Collection date','開始日':'From','終了日':'To','種類':'Type','すべて':'All','雑誌論文':'Journal papers','レビュー':'Reviews','プレプリント':'Preprint','掲載誌':'Journal','すべての掲載誌':'All journals',
'検索する':'Search','条件をクリア':'Clear filters','検索データを読み込んでいます…':'Loading search data…','開始日は終了日以前にしてください。':'The start date must be on or before the end date.',
'論文の表示':'Paper language','検索結果':'Search results','この文献群を解析':'Analyze these papers','並び替え':'Sort by','取り込んだ順 · 新しい順':'Recently collected','公開日 · 新しい順':'Publication date · Newest','さらに30本表示':'Show 30 more','検索結果へ戻る →':'Back to results →',
'対象論文':'Papers','抽出語句':'Extracted terms','公開日が今日まで':'Dated today or earlier','先行公開・未来日付':'Future-dated papers',
'このサイトに収録した論文の傾向です。研究分野全体の流行や網羅的な文献数を示すものではありません。収集範囲の変更でも傾向は変わります。':'These patterns describe papers collected by this site, not the whole research field. Changes in collection coverage also affect the trends.',
'話題のつながり':'Topic connections','表示する語':'Terms to display','共起の最小論文数':'Minimum co-occurrence',
'ドラッグでノードや地図を移動、ホイール・ピンチで拡大縮小。語をクリックすると比較対象に追加できます。':'Drag nodes or pan the map. Scroll or pinch to zoom. Click a term to add it to the comparison.',
'全体を表示':'Fit to view','配置を整える':'Rearrange','円の面積：その語を含む論文数':'Node area: papers containing the term','線の太さ：2語が共起する論文数':'Edge width: papers containing both terms','線の濃さ：共起の強さ（出現頻度で補正）':'Edge darkness: frequency-normalized association','色付きの円：比較に選んだ語（折れ線と同じ色）':'Colored nodes: selected terms (same colors as the lines)',
'語を選ぶと、論文数と関連語を表示します。':'Select a term to see its paper count and related terms.','比較する語を選ぶ':'Choose terms to compare','抽出語を検索':'Search extracted terms','上位10語を選択':'Select top 10','選択をクリア':'Clear selection',
'選択数に上限はありません。多くの語を比べる場合は、下のヒートマップが便利です。':'There is no selection limit. Use the heatmap below to compare many terms.',
'月ごとの変化':'Changes over time','表示方法':'View','折れ線グラフ':'Line chart','ヒートマップ':'Heatmap','指標':'Measure','論文に占める割合':'Share of papers','論文数':'Paper count',
'点にカーソルを合わせて月ごとの数値を確認。語のボタンで選択を解除できます。割合の分母は、その月に公開された検索結果の論文数です。':'Hover over points for monthly values. Click term chips to deselect. Percentages use the number of matching papers published in each month.',
'固定8色のパレットを使用します。9語目以降は線種・点の形も変えて区別します。':'A fixed eight-color palette is used. Additional terms also use different line dashes and marker shapes.',
'多くの語を選択中です。ヒートマップに切り替えると一覧で比較できます。':'Many terms are selected. Switch to the heatmap for an overview.',
'月別の数値を見る':'View monthly data','公開月':'Publication month','語句 / 公開月':'Term / publication month','対象論文に占める割合（%）':'Share of papers (%)',
'この語の論文を見る →':'View papers with this term →','未来日付の論文を見る →':'View future-dated papers →','一致する語がありません。':'No matching terms.',
'上位200語を表示しています。語を入力するとさらに絞れます。':'Showing the top 200 terms. Type to narrow the list.',
'地図または語の一覧から比較する語を選んでください。':'Choose terms from the map or term list to compare.',
'語を選ぶと今日までの公開日の推移を表示します。':'Select terms to see trends for papers dated today or earlier.',
'表示中の語との共起はありません。':'No co-occurrence with the displayed terms.',
'読み込みに失敗しました。通信を確認し、検索ボタンで再試行してください。':'Loading failed. Check your connection and retry the search.','検索データを読み込めませんでした。ページを再読み込みしてお試しください。':'Unable to load search data. Please reload the page.','ネットワークのライブラリを読み込めませんでした。ページを再読み込みしてください。':'Unable to load the network library. Please reload the page.','グラフを読み込めませんでした。数値表をご利用ください。':'Unable to load the chart. Please use the data table.',
'検索に一致する論文がありません。':'No papers match this search.','一致する論文がありません。語句や期間を変えてみてください。':'No matching papers. Try different terms or dates.',
'未来日付':'Future date','公開日不明':'Publication date unknown','要旨を読む':'Read abstract','要旨はありません。':'No abstract available.','原論文を読む ↗':'Read original paper ↗','収録週を見る →':'View archive week →','日本語':'日本語','解除 ×':'Clear ×','トップに戻る':'Back to top','トップに戻る ↑':'Back to top ↑',
'解析方法・データについて':'Methods and data',
'解析は英語タイトル・要旨が対象です。複合語句、頻出する2語の組み合わせ、一般語を除いた単語を抽出しています。同じ語が何度現れても1論文につき1回と数えます。語の抽出は自動処理であり、著者キーワードや専門家による分類ではありません。':'Terms are extracted automatically from English titles and abstracts using phrases, frequent word pairs and words excluding common terms. Each term is counted once per paper. These are not author keywords or expert classifications.',
'検索・解析は表示言語によらず同じ文献群を使います。地図は検索結果内で出現数の多い語と、出現頻度で補正した共起関係を表示します。配置の距離は意味の近さを厳密に示すものではありません。語の選択は地図と推移の母集団を変えず、下の文献一覧を絞ります。':'Both UI languages use the same papers. The network shows frequent terms and frequency-normalized co-occurrence. Layout distances are not exact semantic distances. Selecting comparison terms does not change the underlying set of papers. Use a node’s paper button to filter the results.',
'未来日付の論文も検索と共起集計に含みます。月別推移には今日までに公開された日付の論文だけを含め、未来日付・日付不明は別に集計します。取り込み日が未記録の場合は初回発見日を使用します。件数の少ない月の割合は大きく変動します。':'Future-dated papers are included in search and co-occurrence but excluded from monthly trends. Unknown dates are also reported separately. First-seen dates are used when collection dates are missing. Percentages in months with few papers can fluctuate considerably.'
}));
function translate(value){
 const s=String(value);if(dictionary.has(s))return dictionary.get(s);
 return s.replace(/^全([\d,]+)本 · アーカイブを含む$/,'$1 papers · including archives')
 .replace(/^([\d,]+)本が一致しました。$/,'$1 matching papers.')
 .replace(/^([\d,]+)本$/,'$1 papers').replace(/^(\d+)年$/,'$1')
 .replace(/^([\d,]+)語$/,'$1 terms').replace(/^(\d+)語を選択中$/,'$1 terms selected')
 .replace(/^対象 (\d+)本$/,'$1 papers').replace(/^(\d+)本 · /,'$1 papers · ')
 .replace(/^あとで読む (\d+)$/,'Read later $1')
 .replace(/^先行公開・未来日付：(\d+)本$/,'Future-dated papers: $1')
 .replace(/^検索・共起集計には含み、月別推移には含めていません。日付不明：(\d+)本。$/,'Included in search and co-occurrence, excluded from monthly trends. Unknown dates: $1 papers.')
 .replace(/^(.*?)([\d,]+)本を解析中。検索結果タブに戻っても条件は維持されます。$/,'$1Analyzing $2 papers. Your search is preserved when switching tabs.')
 .replace(/^共起する語：/,'Related terms: ').replace(/（(\d+)本）/g,' ($1 papers)')
 .replace(/^検索データ更新：/,'Search data updated: ')
 .replace(/の選択を解除$/,': deselect').replace(/ で絞り込み/,' filter').replace(/([\d,]+)本/g,'$1 papers');
}
function install(document,getLanguage){
 if(!document.createTreeWalker)return ()=>{};
 const source=new WeakMap(),attributes=new WeakMap();
 const skip=node=>node.parentElement?.closest('script,style,h3[lang],.paper-abstract');
 function apply(){
  document.documentElement.lang=getLanguage();
  const walker=document.createTreeWalker(document.body,4);let node;
  while((node=walker.nextNode())){
   if(skip(node))continue;
   const current=node.nodeValue,prior=source.get(node),original=prior&&current===prior.rendered?prior.original:current;
   const trimmed=original.trim(),translated=getLanguage()==='en'?translate(trimmed):trimmed;
   const rendered=original.replace(trimmed,translated);source.set(node,{original,rendered});if(current!==rendered)node.nodeValue=rendered;
  }
  document.querySelectorAll('[placeholder],[aria-label]').forEach(el=>{
   const saved=attributes.get(el)||{};
   for(const name of ['placeholder','aria-label']){if(!el.hasAttribute(name))continue;const current=el.getAttribute(name),prior=saved[name],original=prior&&prior.rendered===current?prior.original:current,rendered=getLanguage()==='en'?translate(original):original;saved[name]={original,rendered};if(current!==rendered)el.setAttribute(name,rendered)}attributes.set(el,saved);
  });
 }
 if(typeof MutationObserver!=='undefined')new MutationObserver(apply).observe(document.body,{subtree:true,childList:true,characterData:true});
 apply();return apply;
}
root.ExplorerI18n={translate,install};
if(typeof module!=='undefined'&&module.exports)module.exports={translate};
})(typeof window==='undefined'?globalThis:window);
