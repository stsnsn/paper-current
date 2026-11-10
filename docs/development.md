# 開発・運用ガイド

[READMEへ戻る](../README.md) · [公開サイト](https://stsnsn.github.io/paper-current/)

現在の運用：[Actionsによる自動運用](cloud-operations.md)。設計と検証結果は[検討メモ](actions-feasibility.md)を参照してください。

コマンドとファイルパスは、特記がない限りリポジトリのルートを基準にしています。

- [ローカル自動運転](#ローカル自動運転)
- [翻訳と再試行](#翻訳と再試行)
- [テスト](#テスト)
- [日次更新・週単位のアーカイブ](#日次更新週単位のアーカイブ)
- [ランダム出題と論文一覧の検索](#ランダム出題と論文一覧の検索)

## サイトの概要

海洋微生物・微生物ゲノミクスの新着論文を、5問ずつ読む雑誌予想クイズ。トップは新着論文一覧で、初回取り込み分は論文公開日の週ごとに整理した過去問アーカイブから読めます。

- タイトルで予想 → アブストラクトで再予想 → 結果確認。
- 「もう5問」、途中再開、あとで読む保存。
- 案内文はEnglish／日本語切り替え。タイトル・アブストラクトは本文の日本語／Englishボタンで、どちらか一方だけを表示します。本文言語の初期値はページ全体の設定言語に合わせます。同じページ内では両モードで共通の言語を使い、本文側で手動変更した後はページ言語を変更しても本文の選択を維持します。再読み込み時はページ言語を初期値にします。
- bioRxivはタイトルと要旨を読んで掲載先を自由に予測。選択肢や正誤採点はありません。
- DOIを正規化し、改訂版や公式に対応付けられた出版版の重複を防止。
- 今週を含む収録済みの号は、年／月を選んで遊べる過去問アーカイブ。

## 試す

`preview.html`は翻訳済みの現在データを含む単体プレビューです。雑誌4択とbioRxiv自由予測を切り替えてテストできます。最新のローカル訳文を反映する場合は`python scripts/refresh_local_issue.py`、続いて`python scripts/sync_journal_profiles.py`を実行します。push確認済みの号はローカル更新できません。過去問はGitHub Pages上、または`python scripts/serve.py`で配信したページから利用してください。体験用の固定データ10本は`docs/data/demo.json`に残しています。

## 確定した運用構成

**GitHub Actions：RSS/API収集 → PLaMo 3 Translate 2B・4並列翻訳 → 日次追記・週単位の号 → Pages公開**

手元PCの常駐は不要です。設定・状態保存・再開方法は[Actionsによる自動運用](cloud-operations.md)にまとめています。以下のローカル実行手順は、開発・手動作業・代替運用のために残しています。クラウドの自動公開と同時には起動しないでください。

## GitHubへ初回アップロード

1. このフォルダの内容をリポジトリのルートへアップロード。隠しフォルダ`.github`も含める。
2. Settings → Pages → Sourceを **GitHub Actions** に設定。
3. デフォルトブランチを`main`にする。異なる場合は`pages.yml`と`config/automation.json`のbranchを変更。
4. `pages.yml`が`docs/`を公開します。初回に動かなければActionsからPublish quizを手動実行。

GitHub Pagesはmainへのdocs/の変更を受けて自動更新します。

## ローカル自動運転

Python 3.10+、Git、LM Studioを使用。PLaMo 3 Translateをロードし、Local Serverを`http://localhost:1234`で起動してください。

```bash
python -m pip install -r requirements.txt
python scripts/auto.py
```

最初に収集し、以後24時間ごとに再収集。15分ごとに未翻訳分を処理します。毎日09:00 JST以降の処理で、その時点で翻訳済みの新規論文を今週号へ追記します。公開データの変更は1日1回で、追加がない日は書き換えません。公開失敗時は次の処理で同じ版を再送します。

GitHubへのpushまで自動化する場合：

```bash
python scripts/auto.py --publish
```

1回だけ実行する場合は`--once`を追加。停止はCtrl+C。PCとLM Studioが停止している間は処理されず、再起動後に保存済みの続きから再開します。OSの自動起動設定は本試作では変更しません。

### Git接続

通常は本フォルダの`origin`を送信先として使用します。GitHubへpushできる認証とGitのuser.name / user.emailをあらかじめ設定してください。GitHub CLIは不要です。

Gitリポジトリではないフォルダで動かす場合は、`config/automation.json`の`remote_url`にリポジトリURLを設定し、Gitのユーザー名・メールはグローバル設定を使ってください。URLにトークンを埋め込まず、通常のGit認証を使用してください。

自動更新は**一時的なpartial/sparse clone**で行います。最新の問題と小さなアーカイブ索引だけを取得し、今週号の問題JSONへ追記してcommit/pushします。一時cloneは終了時に削除するため、新しい過去問のGitオブジェクトは元のソースリポジトリに蓄積しません。同じ号がリモートに存在する場合、進行中の今週号に限り、既存論文の完全一致と末尾への追加を検証して更新します。過去号の変更や既存論文の変更・並び替えは拒否します。force pushは行いません。

ネットワークエラーやpush失敗時は、生成した問題JSONを手元に残して次回に再試行します。push成功を確認するまでは削除しません。

## 過去問とローカル容量

設定：`config/automation.json`

| 設定 | 初期値 | 内容 |
|---|---:|---|
| archive_after_days | 0 | 日次運用では今週を含め待機期間なしでアーカイブへ表示。週次方式では公開からの日数 |
| local_retention_days | 90 | push済みの出題論文をローカル翻訳キューに保持する期間 |
| collect_interval_hours | 24 | RSS/APIの収集間隔 |
| poll_seconds | 900 | 未翻訳分を確認する間隔 |
| max_papers_per_cycle | 20 | 1巡の翻訳処理件数 |
| publish_weekday | 0 | 旧週次方式での生成曜日（月曜=0） |
| publish_hour_jst | 9 | 公開データを生成できる時刻（日本時間） |

日次運用では今週を含む収録済みの号を、待機期間なしで週単位のアーカイブへ表示します。`archive_available_at` と `week_ends_at` は表示を遅らせる条件には使いません。旧週次方式で公開後半年を表示基準にする場合は `archive_after_days` を180へ変更し、次回の公開時に索引へ反映します。

- 全問題のJSONはGitHubに保存。
- ブラウザは小さな索引だけを最初に取得し、選択した号の問題だけを追加取得。
- 年／月は論文の出版日ではなく、クイズ公開日を基準にする。
- push済みの過去号の問題JSONはローカルの作業フォルダから削除。日次追記に使う今週号は保持。
- 90日経過したpush済み論文は`work/inbox.json`と`work/translated.json`から削除。
- `docs/data/archive-index.json`には日付・問題数・DOI対応・ハッシュだけを保持し、本文がなくても重複出題を防ぐ。
- 未公開・push失敗のデータは削除しない。翻訳待ちなどの未出題候補は別途保持するため、必要に応じて整理する。

別途通常の`git clone`で全履歴を取得したり、手動で過去問JSONをダウンロードした場合、そのコピーは自動削除の対象外です。

## 翻訳と再試行

LM Studio APIは公式PFML3形式の`/v1/completions`で呼び出します。モデルは通常自動特定。複数のPLaMoがある場合はconfigのmodelに正確なIDを設定。認証有効なら環境変数`LM_STUDIO_API_KEY`を使用し、Gitへ保存しないでください。

入力とモデルが同じ翻訳は再利用。原文変更時は該当フィールドだけ再翻訳。タイトル・アブストラクトごとに保存し、1件の失敗で他を止めません。失敗分は15分〜最大24時間の間隔で再試行。生成上限による切断も検出します。訳の意味の正確性は別途確認が必要です。

`work/auto.log`に処理ログ、`work/status.json`に件数と最終実行時刻、`work/translation-retries.json`に失敗情報を保存します。

## 収集・同一文献判定

`config/sources.json`でRSS・検索語を変更できます。RSS、Europe PMC、bioRxiv公式APIを使用。海洋系または広域ゲノム微生物系に一致する論文を候補に保存します。上位件数で打ち切らず、APIはページを最後まで取得して途中失敗をreportに残します。

DOIの大文字小文字、doi.org URL、URLエンコード、bioRxivのバージョン付きURLを正規化。10.1101と10.64898のbioRxiv DOIに対応します。プレプリントと出版版は公式の対応DOIで統合し、似たタイトルだけでは統合しません。対応情報がない異なるDOI間の重複は判別できません。

Cameron Thrash本人の実運用設定との一致は未確認。公開リストのDOI配列JSONはcollect.pyの`--reference-dois`で追加照合できますが、本人の配信リストを自動取得する機能は未実装です。

## 公開対象と制約

- DOI、原文と日英訳が揃った原著／review／プレプリントを対象にします。全配信元でライセンスによる採否判定を行わず、ライセンス情報・旧公開可否フラグも保存しません。
- reviewも対象です。旧 `rights_status` が pending の保存済み論文も、通常の条件を満たせば処理対象です。
- 未出版のbioRxivは予想のみ記録し、正解率の分母から除外。出版後の予想の自動採点は未実装。
- 開始前にBeginner（幅広い4択）／Professional（スコープが近い候補を優先、登録済みの同年度IFも加味）を選択できます。モード別に進捗を保存。IF未登録の雑誌はスコープで選びます。
- 全問完了後は「2周目へ」で再挑戦できます。前の周回の回答と、あとで読む保存は保持されます。
- 静的データには正解が含まれるため、不正防止やランキングはありません。
- 保存・回答はブラウザ内。ブラウザのデータ削除で消えます。保存一覧はJSON／CSVで書き出せます。CSVはUTF-8 BOM付きで、タイトルの日英・雑誌名・DOI・リンクを含みます。
- 日次運用では今週号へ末尾追記し、既存論文と過去号は変更しません。旧週次方式では公開後の号を固定します。
- 手元PCのLM Studio（plamo-3-translate-2b）で翻訳し、GitHub Pagesで公開しています。模擬API・ローカルGitリモート・JavaScriptの動作テストで検証します。

## テスト

```bash
python -m unittest discover -s tests -v
npm test
```

## 参考

- https://github.com/thrash-lab/rss_agent_claude （設計参考、コード転用なし）
- https://github.com/kuroppy/weekly_paper_digest （検索範囲参考、コード転用なし）
- https://huggingface.co/pfnet/plamo-3-translate-8b-GGUF
- https://lmstudio.ai/docs/developer/openai-compat
- https://api.biorxiv.org/

## モードの選択肢データ

`docs/journal-options.js`で雑誌スコープの編集用分類と、年度・出典付きIFを管理します。Professionalは近い候補5誌から選び、毎回の4択を固定しすぎないようにします。未出版プレプリントは論文のテーマから候補を選びます。

登録IFの出典：[Nature Portfolio](https://www.nature.com/nature-portfolio/about-journals/journal-metrics)、[The ISME Journal](https://academic.oup.com/ismej/pages/about)、[ISME Communications](https://academic.oup.com/ismecommun/pages/about)。スコープ分類は本クイズ用の編集判断です。

収集で判明した雑誌名と論文テーマ由来のスコープを`work/journal-catalog.json`に累積し、新しい号の`journal_catalog`へ含めます。翻訳待ちの候補から判明した雑誌も、選択肢の候補になります。RSSは`config/sources.json`の`feed_journals`で掲載誌名を対応付けます。bioRxiv自体は雑誌の選択肢に含めません。

候補カタログが更新された場合、未回答の問題は4択を再生成し、回答途中・回答済みの選択肢は維持します。次の周回では選択肢を再生成します。日次運用では公開済みの選択肢生成用カタログを固定します。新たに収集した雑誌は、次の号のカタログ生成から反映されます。既知の雑誌は編集用スコープ・年度付きIFを優先し、新規誌は収集論文のテーマで補います。

## 初回の全件ローカル翻訳と雑誌集計

```bash
python scripts/translate.py work/inbox.json --keep-going --include-pending
python scripts/summarize_journals.py
```

`--include-pending`は互換用のオプション名です。このオプションでは要旨のない候補もタイトルだけ翻訳します。原文タイトルのない候補はスキップし、完了済みの同一原文・モデルの訳文は再利用します。

集計は`work/journal-summary.json`、累積雑誌カタログは`work/journal-catalog.json`、ブラウザ向けデータは`docs/data/observed-journals.js`へ保存します。bioRxivの件数はプレプリントサーバーとして別計上し、掲載誌はRSSの設定対応表または確定した掲載誌メタデータを使用します。取得できていない掲載先は推測しません。

## 雑誌4択とbioRxiv自由予測

開始画面で「雑誌論文・4択クイズ」と「bioRxiv・自由予測」を切り替えます。Beginner／Professionalは雑誌4択側だけに適用し、切り替えてもスクロール位置を保持します。bioRxivはタイトル・要旨を同時表示し、選択肢や正誤採点を設けません。各モードの履歴と周回は独立しています。

`config/sources.json`の`source_journals`で収集先、スコープ、フィルタ方式を管理します。微生物専門誌・review専門誌は`filter: none`、一般誌は`strict`です。一般誌はタイトルか要旨の明示的な微生物語・属名で判定し、海洋・DNA・進化はテーマ分類にも利用します。bioRxivは微生物語または海洋語がある候補を採用します。判定は正規表現・設定語だけで行い、LLMは翻訳にだけ使用します。NAR／NAR Genomics and Bioinformatics／Bioinformaticsは手法論文を拾うため、現在は無条件採用の設定です。

採否理由は各レコードの`topic_filter`と収集出力の`.filter.json`、RSS/APIの成功・失敗は`.report.json`の`coverage`に記録します。除外した保存済みレコードは削除せず、`scripts/refilter.py`で設定変更後に再判定できます。RSS要旨を保持し、不足分は雑誌名指定のEurope PMC検索で補います。RSSが403等でも、その配信元の失敗を隠しません。

```bash
python scripts/translate_queue.py --include-pending --workers 2
```

`--workers 2` は1つのワーカー内で翻訳リクエストを2並列にします（省略時は1）。保存は直列で行い、翻訳済みフィールドを再利用します。LM Studio側の並列処理能力により速度は変わります。複数ワーカーの同時起動はしないでください。

雑誌由来を先に、次に関連bioRxivだけをPLaMoで翻訳します。雑誌間は順に一件ずつ回して偏りを抑え、途中結果を保存します。進捗は`work/translation-status.json`、訳文は`work/translated.json`です。このコマンドは号の生成・公開・pushを行いません。

追加誌は`python scripts/sync_journal_profiles.py`で選択肢のプロファイルと単体プレビューにも同期できます。

「あとで読む＋」の追加／解除は、雑誌4択・bioRxivの両方でスクロール位置を保持します。保存一覧のJSON／CSV出力は同じ保存レコードから生成します。

4択クイズの「01 タイトル」には「この論文をスキップ」があります。スキップは回答・正解率の分母から除外して別表示し、読了の進捗には含めます。全件を回答またはスキップすると次の周回へ進めます。

ホームの「最初からやり直す」は、現在選択中のモードの回答・スキップ・周回履歴を初期化して1問目から開始します。他のモードの進捗、本文言語、「あとで読む」は保持します。

論文モード・難易度・「最初からやり直す」の簡易説明は、ホバーまたはキーボードフォーカスで表示します。Escapeキーで説明を閉じられます。

## Europe PMCの要旨・DOI補完

検索APIのcore応答でも、PMC由来のレコードは要旨・DOIが空欄の場合があります。`scripts/epmc_metadata.py`で、該当PMCIDの本文XMLから主論文の英語要旨・DOI・PMID・掲載日を補完します。キーワード、補足情報、図だけの要旨は本文要旨に混ぜません。XMLの識別子と検索レコードが食い違う場合は補完を拒否します。

補完結果は`work/cache/europepmc/`に保存し、収集レポートの`metadata_enrichment`へ件数と失敗を記録します。DOI・PMCID・PMIDの明示的な対応で重複を統合し、原文が同一なら完了済みタイトル訳を再利用します。ライセンス情報の補完や保存は行いません。

## 日次更新・週単位のアーカイブ

`publication_mode: "daily"` が既定です。月曜00:00 JSTで週を区切り、号ID（例：2026-W46）はその週の間固定します。初回の一括取り込みだけは論文公開日のISO週で過去問を再構成しました。以後の新規論文は収録週に所属し、遅れて見つかった古い論文も収録週に入ります。新着一覧は収録日を優先して直近7日を表示し、公開日順に並べます。過去問は年・月から選び、号内の論文はブラウザ側で公開日順に並べ替えられます。

- 毎日09:00 JST以降、翻訳済みの未掲載論文が1本でもあれば追記します。その日すでに版を生成した場合、追加分は翌日へ回します。追加がなければ公開しません。
- 公開済みの論文・順序を維持し、新規論文だけ末尾へ追加します。今週号の選択肢生成用のカタログも固定し、進捗と選択肢を保存します。
- 5問未満の週初めにも対応し、一度終えた後に問題が増えても未回答の続きへ進めます。言語・難易度・雑誌/bioRxiv別の進捗は従来どおりです。
- 前週号は翌週月曜00:00 JSTから過去問として表示します。新しい週に翻訳済み論文がまだないときは、前の号をトップに残します。
- トップには最終更新時刻と、本日追加された論文数をモード別に表示します。
- 公開の確認は号IDだけでなくSHA-256で管理します。今週号の本体は公開後もローカルに残し、翌日の追記に使用します。ローカルの翻訳キューの保持期間は引き続き90日です。

自動公開は従来どおり `python scripts/auto.py --publish` で有効にします。`auto_push: false` のままなので、`--publish` を付けない実行はデータ生成までです。起動中の `translate_queue.py` と同時起動しないでください。同じロックを使い、二重実行を拒否します。既存の翻訳処理が終了してから切り替えます。OSの常駐設定は変更しません。

既存の設定を使う場合、`archive_after_days` は日次運用では0、`archive_policy` は索引で `weekly` になります。週次の凍結方式を必要とする既存連携は `publication_mode: "weekly"` で従来の動作を利用できます。

## ランダム出題と論文一覧の検索

クイズは未回答の論文をランダムな順に出題します。順番は号・モード・周回ごとにこのブラウザへ保存し、途中再開でも維持します。回答済み・スキップ済みは同じ周では再出題せず、日次追加分は保存済みの順番の末尾に加えます。従来の進捗も引き継ぎ、途中のラウンドとタイトルへの回答を保持します。「もう一周」や「最初からやり直す」では順番を作り直します。

新着論文一覧では、表示言語に関係なく日英のタイトル・要旨とDOIを検索できます。英字の大文字・小文字や全角・半角は区別せず、スペース区切りの複数語はすべてを含む論文に絞ります。デフォルトは論文公開日（新しい順）。サイト追加順、表示言語のタイトル順、IF順（2025年・高い順）にも切り替えられます。公開日不明の論文は公開日順の末尾に表示します。IFは出版社の公表値とABS Nexoraの公開JCR検索を使い、確認できない誌はJCR検索へのリンクを表示します。新創刊などJIF未付与と確認できた誌は理由を表示します。検索・並び替えは出題順や回答履歴に影響しません。

IF順のデータは `docs/data/journal-metrics.js` で管理します。2026年11月6日に出版社・学会の公式ページで確認した2025年の2年Journal Impact Factor（2026年公表）39誌を収録し、各値に出典URLを付けています。2025年公表の2024年JIF、5年IF、CiteScoreは混在させません。確認できない値は推測・ゼロ埋めをせず、bioRxivとともに末尾へ並べます。雑誌名の表示をオンにすると、確認済みIFと出典リンクも表示します。eLifeのような未付与のケースも数値を補いません。クイズの既存選択肢を変えないため、一覧用のIFデータは出題用プロファイルとは独立して管理します。

### トップのナビゲーション

上部に論文一覧・雑誌論文4択クイズ・bioRxiv・過去論文アーカイブを配置します。アーカイブの年・月・週選択は独立した画面で開きます。過去の号を開いた後は、選択中の週を見出しに表示し、4つ目を「新着論文一覧へ戻る」に切り替えます。スクロール操作は上向き矢印の丸ボタンで示し、読み上げ名とツールチップを「ページの先頭へ」にしています。

## 4択生成専用のIF

`config/quiz-journal-metrics.json` を編集し、`python3 scripts/sync_journal_profiles.py` で `docs/journal-options.js` のプロフィールへ反映します。元の91誌と追加したASM Animal Microbiologyの計92誌に正の数値を登録しています。値・対象年・出典・確認日・種類（publisher / third_party / existing_reference / historical / unofficial / proxy）を保持します。existing_referenceは既存の画面表示用データから引き継いだ値です。

Professionalの距離計算では、分野タグの距離に、IF比の自然対数の絶対値（上限1）×0.35を加えます。対象年が異なる場合も、利用可能な過去値を比較に使います。eLifeは2023年の6.4、microLifeは第三者サイトの非公式値3.17です。ISME Host MicrobeはISME Communicationsの6.4、ASM Animal Microbiology（別名Animal Microbiology）はAnimal Microbiomeの4.5を借用します。proxyは当該誌の実測JIFではありません。

このデータは選択肢生成にだけ使います。画面表示・IF順ソートは引き続き `docs/data/journal-metrics.js` を使用し、仮IF・過去値・非公式値をそこへ自動転記しません。既に回答中の選択肢は保持します。

## Europe PMCの新着判定と分類群の横断検索

Europe PMCは登録日（`FIRST_IDATE`）と初回公開日（`FIRST_PDATE`）の両方で絞ります。登録日の開始日は配信元ごとの成功カーソルから決め、初回公開日は実行日の21日前以降（未来日付を含む）（`config/sources.json` の `europepmc_publication_days`）に固定します。古い論文が新規登録されても新着には採用しません。XML補完後の `firstPublicationDate` も再検証し、下限より古い日付・日付不明を除外します。既存の保存済み論文を遡って削除する処理ではありません。

`europepmc_watchlist` の SAR11、Pelagibacter、Poseidoniales、SAR86 は、タイトルまたは要旨に含まれる論文を独立して検索します。掲載誌リストや除外誌設定を問わず採用します（`--journals-only` 時はプレプリントを除外）。通常の分野検索・雑誌検索と併用し、DOI等で重複を統合します。公開日制限と既存の翻訳・公開要件は適用されます。検索式と公開日の下限は収集レポートの `coverage` に記録します。Europe PMC未収載の論文、索引登録が21日以上遅れた論文は対象外です。

SAR11/Pelagibacterのみの一度限りの遡及収集は `scripts/collect.py --out work/sar11-backfill.json --watchlist-backfill-since 2026-05-07`。通常のカーソルを使わず、指定公開日以降を取得し、`archive_only` を付与します。通常収集とは別ファイルに保存してください。表示の初期順は収集日時の降順です。

保存済みのライセンス情報は `scripts/remove_license_metadata.py` で一度削除しました。今後のJSON保存・レコード統合でも `license`、`license_url`、`rights_status` を取り除き、旧フラグによる除外はありません。

## 全体検索と文献解析

`python3 scripts/build_explorer.py` で週別アーカイブ・今週分・新着一覧を統合し、年別検索データを `docs/data/explorer/` に生成します。全件の週別JSONが必要です。通常の新着ページでは検索データを読み込みません。クラウド公開処理でも公開データ更新後に再生成します。

`python3 scripts/serve.py --port 5173` で起動し、`http://127.0.0.1:5173/explore.html?year=2026&query=SAR11` で確認できます。新着ページの「全体検索・解析」からも開けます。検索画面は目録と必要な公開年のデータだけを読み込み、取り込み日で年を絞る場合は全公開年を読み込みます。検索条件はURLに残ります。

英語タイトル・要旨から一般語を除き、辞書の複合語句、繰り返される2語の組み合わせ、単語を抽出します。出現数は1論文につき1回。語数の上限なく月別件数・出現率を比較でき、折れ線とヒートマップを切り替えられます。ノードの「この語の論文を見る」で検索母集団を保ちながら文献一覧を絞ります。未来日付は検索・共起には含め、公開日の月別推移には含めません。表でも同じ数値を確認できます。

サイト内の収録傾向を示すもので、分野全体の流行を推定するものではありません。自動抽出語は著者キーワードではなく、語義・否定表現の解釈は行いません。図の距離も厳密な意味距離ではありません。

検索結果と解析は同じページ内のタブで分離しています。URLの `panel=analysis` で解析を直接開けます。図は解析タブを開いたときに生成します。共起地図はローカル同梱のCytoscape.js 3.33.1で描画し、ズーム・パン・ノードのドラッグ・関連語の強調・再配置に対応。月別推移はChart.js 4.5.1の折れ線とヒートマップで比較します。9語目を選択したときはヒートマップへ切り替え、その後も表示方法を選べます。通常の閲覧ページではこれらのライブラリを読み込みません。

ノードの面積は語を含む論文数に比例します。エッジの太さは共起する論文数、濃さは `共起数 / sqrt(語Aの論文数 * 語Bの論文数)` に対応します。凡例とエッジを選んだときの数値表示で確認できます。比較語には固定8色を順に割り当て、検索し直すまでは解除・再選択しても色を維持します。9語目以降は色に加えて線種と点の形も変えます。UI言語は他ページと同じ保存設定を共有し、検索条件・比較語を維持して切り替えます。論文の原文はUI翻訳の対象にしません。

期間指定は「すべての期間」「各年」「日付を指定」の単一選択です。日付指定時だけ開始・終了日を表示し、年と独立した範囲を同時適用しません。種類・掲載誌・日付の基準は「詳細条件」にまとめ、設定済みの条件数を表示します。期間のラベルは公開日／取り込み日の基準に連動します。検索結果の上には適用済みの条件を表示します。

### Collection scope and manual backfill

`topic_scope.py` owns shared discovery vocabulary. No individual tool name or DOI
is required. Explicit ANI/AAI phrases qualify in a title or a sentence stating a
method or use. General assembly/annotation/phylogeny tools need microbial context,
including microbial eukaryotes. General journals and preprints use the same rules;
marine terms alone do not qualify. Missing abstracts remain metadata-pending.
Corrections/retractions/news and configured excluded journals are checked separately.

Existing `filter: none` journal profiles remain full coverage (including NAR and
Bioinformatics); their names alone are the selection boundary. Other journal queries
only specify a journal and therefore still need one topic check. Europe PMC topic
queries combine microbial/taxon evidence with aquatic/genomics terms in title or
abstract, and record `scope: target`; downstream stages reuse that selection.
The ANI/AAI/metagenome-method query is a candidate query because it can include
background mentions; it gets one local purpose check. bioRxiv official date-range
API and RSS categories such as `genomics` do not establish microbial scope.
`discovery` records preserve the actual query, source and scope across DOI merges.

Run **Manual collection backfill** on main, with `since`, `until`, and routes
`europepmc,biorxiv` for historical coverage across all configured journals and topic
queries plus all bioRxiv categories. Optional `journals` accepts comma-separated
configured names (for example `mSystems,Applied and Environmental Microbiology`).
RSS is optional but feed contents cannot prove historical completeness. Europe PMC
backfill uses publication dates without `FIRST_IDATE` or a normal collection cursor.
Normal collection retains its index-arrival and recent-publication windows.

The default preview uploads `work/backfill/`, including raw candidates, coverage,
`.filter.json` and `backfill-report.json`. The report distinguishes published,
queued, rejected, metadata-pending and translation-pending records. `apply=true`
adds only new DOI/linked-DOI identities against freshly restored durable state and
archive-index; it does not translate or publish. Incomplete collection fails and
cannot apply. Both workflows share `concurrency: pages`; state saves use the same
manifest/checksum implementation. Backfill never advances normal source cursors.

For a DOI investigation, search the daily/backfill `.filter.json` for the DOI,
check the corresponding report's coverage and query, then inspect durable inbox,
translated cache and archive-index separately. Absence from `.filter.json` means
that route did not return it (or has not finished), not a topic rejection. Daily
artifacts include `.filter.json`, checkpointed after each completed page/source.

A versioned `config/backfill-request.json` provides the same manual operation when
only SSH Git authentication is available: commit a changed request (`since`,
`until`, `routes`, optional `journals`, boolean `apply`, and a distinct `id`) to
main. Changing that file triggers the daily workflow. The daily workflow also checks
uncompleted request IDs on every run, so replacement of a pending Actions run
cannot lose the request. Successful IDs are checkpointed in automation-state
before normal collection/translation. An unchanged completed request does not
run again. This uses the same serialized queue and manifest save as the manual
backfill workflow.
