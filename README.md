# Paper Current — prototype v0.4

海洋微生物・微生物ゲノミクスの新着論文を、5問ずつ読む雑誌予想クイズ。

- タイトルで予想 → アブストラクトで再予想 → 結果確認。
- 「もう5問」、途中再開、あとで読む保存。
- 案内文はEnglish／日本語切り替え。タイトル・アブストラクトは常に日英併記。
- bioRxivを含む。未出版の予想は採点せず、掲載先が分かる論文のみ正誤を表示。
- DOIを正規化し、改訂版や公式に対応付けられた出版版の重複を防止。
- 90日を過ぎた号は、年／月を選んで遊べる過去問アーカイブ。

## 試す

`preview.html`を開くと、実在CC BY論文10本（bioRxiv 1本を含む）の体験版を遊べます。訳文は試作用で、PLaMoの実行結果ではありません。過去問はGitHub Pages上、または`python scripts/serve.py`で配信したページから利用してください。配布直後のアーカイブ索引は空です。

## 確定した運用構成

**手元PC：RSS/API収集 → PLaMo翻訳 → 週次データ生成 → git push**

**GitHub Actions：pushを受けてGitHub Pagesを更新するだけ**

GitHub上では収集・翻訳を実行しません。閲覧者のブラウザからLM Studioへの接続も不要です。

## GitHubへ初回アップロード

1. このフォルダの内容をリポジトリのルートへアップロード。隠しフォルダ`.github`も含める。
2. Settings → Pages → Sourceを **GitHub Actions** に設定。
3. デフォルトブランチを`main`にする。異なる場合は`pages.yml`と`config/automation.json`のbranchを変更。
4. `pages.yml`が`docs/`を公開します。初回に動かなければActionsからPublish quizを手動実行。

本作業ではGitHubへの実アップロードは行っていません。

## ローカル自動運転

Python 3.10+、Git、LM Studioを使用。PLaMo 3 Translateをロードし、Local Serverを`http://localhost:1234`で起動してください。

```bash
python -m pip install -r requirements.txt
python scripts/auto.py
```

最初に収集し、以後24時間ごとに再収集。15分ごとに未翻訳分を処理します。週刊クイズは月曜日09:00 JST以降に自動生成します。

GitHubへのpushまで自動化する場合：

```bash
python scripts/auto.py --publish
```

1回だけ実行する場合は`--once`を追加。停止はCtrl+C。PCとLM Studioが停止している間は処理されず、再起動後に保存済みの続きから再開します。OSの自動起動設定は本試作では変更しません。

### Git接続

通常は本フォルダの`origin`を送信先として使用します。GitHubへpushできる認証とGitのuser.name / user.emailをあらかじめ設定してください。GitHub CLIは不要です。

Gitリポジトリではないフォルダで動かす場合は、`config/automation.json`の`remote_url`にリポジトリURLを設定し、Gitのユーザー名・メールはグローバル設定を使ってください。URLにトークンを埋め込まず、通常のGit認証を使用してください。

自動更新は**一時的なpartial/sparse clone**で行います。最新の問題と小さなアーカイブ索引だけを取得し、新しい問題JSONを追加してcommit/pushします。一時cloneは終了時に削除するため、新しい過去問のGitオブジェクトは元のソースリポジトリに蓄積しません。同じ号がリモートに異なる内容で存在する場合は上書きせず停止します。force pushは行いません。

ネットワークエラーやpush失敗時は、生成した問題JSONを手元に残して次回に再試行します。push成功を確認するまでは削除しません。

## 過去問とローカル容量

設定：`config/automation.json`

| 設定 | 初期値 | 内容 |
|---|---:|---|
| archive_after_days | 90 | 公開から何日後に年／月アーカイブへ表示するか |
| local_retention_days | 90 | push済みの出題論文をローカル翻訳キューに保持する期間 |
| collect_interval_hours | 24 | RSS/APIの収集間隔 |
| poll_seconds | 900 | 未翻訳分を確認する間隔 |
| max_papers_per_cycle | 20 | 1巡の翻訳処理件数 |
| publish_weekday | 0 | 週刊生成の曜日（月曜=0） |
| publish_hour_jst | 9 | 週刊生成時刻（日本時間） |

半年に変更するならarchive_after_daysを180へ。公開索引に反映するには次の週刊pushが必要です。

- 全問題のJSONはGitHubに保存。
- ブラウザは小さな索引だけを最初に取得し、選択した号の問題だけを追加取得。
- 年／月は論文の出版日ではなく、クイズ公開日を基準にする。
- push済みの号の問題JSONはローカルの作業フォルダから削除。
- 90日経過したpush済み論文は`work/inbox.json`と`work/translated.json`から削除。
- `docs/data/archive-index.json`には日付・問題数・DOI対応・ハッシュだけを保持し、本文がなくても重複出題を防ぐ。
- 未公開・push失敗のデータは削除しない。利用条件未確認などの未出題候補は別途保持するため、必要に応じて整理する。

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

- 利用条件allowed、DOI、原文と日英訳が揃った原著／review／プレプリントを対象にします。試作ではEurope PMC/bioRxivのCC BYと、bioRxivのCC0を使用。元記事の条件・適用版は公開前に確認してください。
- reviewも対象です。利用条件がpendingの候補は公開しません。
- 未出版のbioRxivは予想のみ記録し、正解率の分母から除外。出版後の予想の自動採点は未実装。
- 開始前にBeginner（幅広い4択）／Professional（スコープが近い候補を優先、登録済みの同年度IFも加味）を選択できます。モード別に進捗を保存。IF未登録の雑誌はスコープで選びます。
- 全問完了後は「2周目へ」で再挑戦できます。前の周回の回答と、あとで読む保存は保持されます。
- 静的データには正解が含まれるため、不正防止やランキングはありません。
- 保存・回答はブラウザ内。ブラウザのデータ削除で消えます。保存一覧はJSONで書き出せます。
- 週刊の公開済み号は固定。同じ号に後から論文を足さず、次号へ回します。
- 手元PCのLM Studio（plamo-3-translate-2b）で20件の翻訳を確認済み。GitHubへの実公開は未実施。模擬API・ローカルGitリモート・ブラウザで検証しています。

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

### モードの選択肢データ

`docs/journal-options.js`で雑誌スコープの編集用分類と、年度・出典付きIFを管理します。Professionalは近い候補5誌から選び、毎回の4択を固定しすぎないようにします。未出版プレプリントは論文のテーマから候補を選びます。

登録IFの出典：[Nature Portfolio](https://www.nature.com/nature-portfolio/about-journals/journal-metrics)、[The ISME Journal](https://academic.oup.com/ismej/pages/about)、[ISME Communications](https://academic.oup.com/ismecommun/pages/about)。スコープ分類は本クイズ用の編集判断です。

収集で判明した雑誌名と論文テーマ由来のスコープを`work/journal-catalog.json`に累積し、新しい号の`journal_catalog`へ含めます。翻訳待ち・利用条件確認待ちの候補から判明した雑誌も、選択肢の候補になります。RSSは`config/sources.json`の`feed_journals`で掲載誌名を対応付けます。bioRxiv自体は雑誌の選択肢に含めません。

候補カタログが更新された場合、未回答の問題は4択を再生成し、回答途中・回答済みの選択肢は維持します。次の周回では選択肢を再生成します。公開済みの号は固定なので、新たに収集した雑誌は次の号の生成・公開から反映されます。既知の雑誌は編集用スコープ・年度付きIFを優先し、新規誌は収集論文のテーマで補います。

### 初回の全件ローカル翻訳と雑誌集計

```bash
python scripts/translate.py work/inbox.json --keep-going --include-pending
python scripts/summarize_journals.py
```

`--include-pending`は利用条件確認待ちもローカルで翻訳します。元の`rights_status`を保持するため、確認待ちの訳文は公開対象になりません。このオプションでは要旨のない候補もタイトルだけ翻訳します。原文タイトルのない候補はスキップし、完了済みの同一原文・モデルの訳文は再利用します。

集計は`work/journal-summary.json`、累積雑誌カタログは`work/journal-catalog.json`、ブラウザ向けデータは`docs/data/observed-journals.js`へ保存します。bioRxivの件数はプレプリントサーバーとして別計上し、掲載誌はRSSの設定対応表または確定した掲載誌メタデータを使用します。取得できていない掲載先は推測しません。
