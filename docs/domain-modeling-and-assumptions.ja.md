# ドメインモデリングと前提

このドキュメントは、`access-governance-warehouse` v0.1.0 におけるドメインモデリング（domain modeling）上の判断と、意図的な単純化前提を説明するものです。

このプロジェクトは、企業向けAIツールのアクセスガバナンス（access governance）を題材にした、ローカルウェアハウス（local warehouse）かつ analytics engineering のポートフォリオプロジェクトです。明示的なウェアハウスモデリング（warehouse modeling）、dbtによる変換、データ品質テスト（data quality testing）、ドキュメント化、lineage（データ系譜）、ビジネス向け分析出力（business-facing analytical outputs）を示すことを目的としています。

目的は、本番用の完全な access governance platform を再現することではありません。  
代わりに、governance、adoption、usage、spend に関する焦点を絞った問いに答えられる、最小限かつ信頼できるウェアハウスモデルを提供することを目的としています。

---

## 1. ドメイン範囲（Domain Scope）

このプロジェクトで扱うドメインは、企業向けAIツールのアクセスガバナンス（access governance）です。

このウェアハウスは、主に次の業務上の問い（business questions）に答えることを目的としています。

1. どのチームが、どのツールを、いつ申請・承認・却下しているか
2. 承認されたツールが実際に使われているか
3. 承認なしの利用があるuser-tool関係はどれか
4. 費用（spend）が導入・定着状況（adoption）や利用状況（usage）と方向性として整合しているか

このドメインは、意図的に分析用ウェアハウス層（analytical warehouse layer）にスコープを絞っています。  
このリポジトリには、プロダクトアプリケーション、承認UI（approval UI）、本番用のオーケストレーション、ライブデータ抽出、クラウドデータウェアハウスへのデプロイは含まれません。

### 関連するアプリケーション文脈

このウェアハウスは、関連する
[`ai-tool-access-requests`](https://github.com/ShikiIchitose/ai-tool-access-requests)
ポートフォリオプロジェクトと概念的に対応しています。  
`ai-tool-access-requests` は、企業向けAIツールのアクセス申請・承認ワークフロー（access request / approval workflow）を扱う、最小構成のDjangoアプリケーションです。

ただし、このリポジトリでは raw data は synthetic かつ file-based です。  
v0.1.0では、そのDjangoアプリケーションからライブデータを抽出しているわけではありません。  
代わりに、アクセス申請アプリケーション、および関連する利用・費用データソースの下流に位置し得る分析レイヤー（analytical layer）をモデル化しています。

application UI は、関連するDjangoアプリケーションのリポジトリ側に属します。  
このリポジトリは、下流のウェアハウスと分析モデリング層（analytical modeling layer）に焦点を当てています。

---

## 2. モデル化している業務エンティティ

v0.1.0 のウェアハウスでは、次の主要なエンティティ（entities）とプロセス（processes）をモデル化しています。

| 領域 | モデル化対象 | 主な目的 |
|---|---|---|
| ツールカタログ（Tool catalog） | 企業向けAIツール | request、usage、spend、governance reportingで使うツール一覧を定義する |
| ユーザーディレクトリ（User directory） | 現在状態のユーザー（current-state users） | user、team、department、job level、employment status といった属性を提供する |
| アクセス申請（Access requests） | 申請ワークフロー行（request workflow rows） | 提出されたaccess requestsと最終review stateを保持する |
| 利用実績（Usage） | 日次user-tool利用（daily user-tool usage） | approved / unapproved tool usage analysisのための日次activityを保持する |
| 費用（Spend） | 月次team-tool費用（monthly team-tool spend） | 月次team-tool粒度のbilled tool spendを保持する |
| ガバナンス例外（Governance exceptions） | user-tool単位のreview signals | usage without approval と approval without recent usage を表面化する |
| adoptionレビュー候補（Adoption review candidates） | 月次team-tool単位のreview signals | approval、usage、spend のalignment issueを表面化する |

---

## 3. レイヤー構造（Layering Model）

このウェアハウスは、layered dbt model structure に従います。

| レイヤー | 目的 |
|---|---|
| Sources | raw Parquet input contractsを定義する |
| Staging | raw grainを保ったままraw fieldsを標準化する |
| Core | 再利用可能なディメンション（dimensions）とファクト（facts）を定義する |
| Intermediate | re-graining、stock logic、mart support logicを切り出す |
| Marts | ビジネス向け分析出力（business-facing analytical outputs）を提供する |

想定する流れは次の通りです。

```text
raw sources -> staging -> core -> intermediate -> marts
```

このレイヤー構造により、低レベルのsource整形、再利用可能なウェアハウス上の意味づけ（warehouse semantics）、ビジネス向け分析出力を分離しています。

---

## 4. source data の前提

raw層（raw layer）は、このプロジェクト用に生成された、決定論的なsynthetic Parquet filesで構成されます。

5つのraw source tablesは次の通りです。

| Source | 粒度（Grain） |
|---|---|
| `raw_tool_catalog` | toolごとに1行 |
| `raw_user_directory` | userごとに1行 |
| `raw_access_requests` | access requestごとに1行 |
| `raw_usage_events_daily` | recorded activity があるuser、tool、dayごとに1行 |
| `raw_tool_spend_monthly` | billed month、team、toolごとに1行 |

raw files は、dbtに対するsource contracts（ソース契約）として扱います。  
warehouse側では、source-level structure（source層の構造）、accepted values、keyの存在、必要に応じた一意性（uniqueness）、foreign key-like resolvability（外部キーに近い値の参照解決可能性）を検証します。

generator側のQA(Quality Assurance:品質保証)は、決定論的な出力、rawファイルの存在、rawカラム順序の一致、行数の観測可能性、generator固有のビジネスルール実現を検証します。

---

## 5. モデル粒度の概要

各 downstream dbt model は、明示的な粒度（grain）を持つように設計されています。  
ここでいう粒度とは「1行が何を表すのか」を定義するものであり、そのモデルから安全に答えられる問いの範囲を決めるものです。

### Staging models

staging models は、上流の raw source の粒度を維持します。  
フィールド名（field name）、型（type）、軽量な行レベルの補助項目（row-level helper fields）を標準化しますが、結合（join）や集約（aggregation）は行いません。

| Model | 粒度（Grain） |
|---|---|
| `stg_access_governance__tool_catalog` | toolごとに1行 |
| `stg_access_governance__user_directory` | userごとに1行 |
| `stg_access_governance__access_requests` | access requestごとに1行 |
| `stg_access_governance__usage_events_daily` | user、tool、usage dateごとに1行 |
| `stg_access_governance__tool_spend_monthly` | billed month、team、toolごとに1行 |

### Core models

core models は、再利用可能な dimension と fact を定義します。  
dimensions は entity-grained（エンティティ粒度）であり、facts はそれぞれが表す business process（業務プロセス）または measure（測定値）の粒度を維持します。

| Model | 粒度（Grain） |
|---|---|
| `dim_tool` | toolごとに1行 |
| `dim_user` | userごとに1行 |
| `fct_access_request` | access requestごとに1行 |
| `fct_tool_usage_daily` | user、tool、usage dateごとに1行 |
| `fct_tool_spend_monthly` | billed month、team、toolごとに1行 |

### Intermediate models

intermediate models は、re-graining（粒度の組み替え）、stock logic（時点状態のロジック）、再利用可能な mart support logic（mart支援ロジック）を分離するためのモデルです。  
end-user-facing outputs（最終利用者向けの出力）ではありません。

| Model | 粒度（Grain） |
|---|---|
| `int_access_requests_open_at_month_end` | reporting month、open access requestごとに1行 |
| `int_tool_usage_aggregated_to_month_team_tool` | reporting month、team、toolごとに1行 |
| `int_user_tool_approved_current` | user、toolごとに1行 |
| `int_user_tool_approved_as_of_month_end` | reporting month、user、toolごとに1行 |
| `int_user_tool_recent_usage_30d` | recent usage activity があるuser、toolごとに1行 |

### Mart models

marts は、business-facing analytical outputs（ビジネス向けの分析出力）です。  
その粒度は、report metrics（レポート指標）をどのレベルで解釈すべきかを決めます。

| Model | 粒度（Grain） |
|---|---|
| `access_requests_monthly` | reporting month、team、toolごとに1行 |
| `tool_adoption_monthly` | reporting month、team、toolごとに1行 |
| `adoption_review_candidates_monthly` | reporting month、team、toolごとに1行 |
| `governance_exceptions_current` | user、toolごとに1行 |

### Implication

metrics（指標）は、それを公開している model の粒度で解釈する必要があります。  
ある business question（ビジネス上の問い）が別の粒度を必要とする場合、downstream report（下流レポート）が集約済み row から失われた詳細を推測するのではなく、warehouse 側でその粒度の model または mart を公開するべきです。

---

## 6. current-state user directory の前提

user directory は current-state only（現在状態のみ）としてモデル化します。

これは次を意味します。

- `dim_user` にはuserの現在のteamとdepartmentが含まれる
- request attribution と usage attribution には、現在状態のuser属性を使用する
- 過去のteam所属履歴（historical team membership）は再構築しない
- v0.1.0では slowly changing dimension behavior はモデル化しない

これは意図的な単純化です。

例えば、あるuserが現在Analytics teamに所属している場合、そのuserのhistorical usageは、実際の本番systemでは過去に別teamに所属していた可能性があっても、Analyticsに紐づけられます。

これにより、モデルを確認しやすくし、v0.1.0ではhistorical organization modelingではなくwarehouse modelingに焦点を保ちます。

### 含意

teamまたはdepartmentでgroupingした指標は、as-of-event historical attributionではなく、current-state attributionとして解釈する必要があります。

---

## 7. access request modeling の前提

access requests は、request-level final-state rows（申請単位の最終状態行）としてモデル化します。

`raw_access_requests` と `fct_access_request` の各行は、1つのaccess requestを表します。

requestは次の情報を持ちます。

- requester-side context（申請者側の文脈）
- requested tool（申請されたtool）
- request purpose（申請目的）
- data classification（データ分類）
- final request status（最終申請ステータス）
- review済みの場合のreview-side fields（レビュー側フィールド）

対応するrequest statusesは次の3つです。

- `approved`
- `rejected`
- `pending`

review-side fields は、status-aware（statusに応じて値の有無が変わる）です。

| Status | `reviewed_at` | `reviewed_by_user_id` | `review_comment_text` |
|---|---|---|---|
| `approved` | 値あり | 値あり | optional |
| `rejected` | 値あり | 値あり | 値あり |
| `pending` | null | null | null |

つまり、pending request の null review fields は、missing data（欠損データ）ではなく、意図されたworkflow state（ワークフロー状態）です。

---

## 8. approval persistence と revocation の前提

v0.1.0では、revocation（アクセス剥奪）はモデル化していません。

user-tool pair にapproved requestが一度存在すると、そのapproved accessは、downstreamのcurrent-state logicおよびmonth-end stock logicにおいて持続するものとして扱います。

この前提は、次のモデルに影響します。

- `int_user_tool_approved_current`
- `int_user_tool_approved_as_of_month_end`
- `tool_adoption_monthly`
- `governance_exceptions_current`

### 含意

approved-access stock は時間とともに蓄積され得ます。  
テストとmartは、将来versionでrevocationが導入されない限り、approved accessが減少しないことを前提にできます。

将来revocationを導入する場合は、approved-access stock logicと、単調性（monotonicity）を前提にするテストを見直す必要があります。

---

## 9. usage modeling の前提

usage は、event grain（1回の利用イベントごとに1行）ではなく、daily aggregated grain（user、tool、usage dateごとに1行の日次集計粒度）でモデル化します。

usage fact のgrainは次の通りです。

| モデル | 粒度（Grain） |
|---|---|
| `fct_tool_usage_daily` | user、tool、usage dateごとに1行 |

raw generatorは、recorded activity（記録された利用activity）がある user-tool-day combinations のみをusage rowsとして出力します。  
zero-activity combinations（activityがない組み合わせ）はraw rowsとしてmaterializeされません。

usage metricsには次が含まれます。

- `session_count`
- `prompt_count`
- `input_tokens_total`
- `output_tokens_total`

warehouseはこれらの指標から次を導出します。

- monthly team-tool usage
- active user counts
- recent 30-day usage state
- governance exception signals

### 含意

usage rowが存在しないことは、「生成されたzero rowが存在する」ことを意味しません。  
そのuser-tool-day combinationについて、recorded activityがmaterializeされなかったことを意味します。

---

## 10. recent usage window の前提

recent usage は、30日windowとして定義します。

recent usage window は、system clockではなく、warehouse内の最大 `usage_date` を基準にします。

これにより、local環境でprojectを実行する日付に結果が依存しないため、projectの再現性が保たれます。

recent usage logic は次で使用されます。

- `int_user_tool_recent_usage_30d`
- `governance_exceptions_current`

### 含意

recent usage は、今日の実世界日付ではなく、生成されたdataset内の日付を基準に解釈する必要があります。

---

## 11. spend modeling の前提

spend は、monthly team-tool grain（月次team-tool粒度）でモデル化します。

spend fact のgrainは次の通りです。

| モデル | 粒度（Grain） |
|---|---|
| `fct_tool_spend_monthly` | billed month、team、toolごとに1行 |

spend rows は、billed combinations（請求対象となった組み合わせ）のみを表します。

つまり、すべてのmonth、team、toolの組み合わせが `raw_tool_spend_monthly` または `fct_tool_spend_monthly` に存在するとは限りません。

spend rowが存在しないことは、reporting spineにjoinしたときに意味を持つ場合があります。  
例えば、mart rowにusage activityはあるがbilling rowがない場合、その状態はfinanceまたはprocurement向けのreview candidateとして表面化できます。

### 含意

raw spendおよびspend factsに存在するspend rowsでは、spend fieldsには値が入っているべきです。

一方、martsでは、reporting month、team、toolの組み合わせに対してbilling rowが存在しない場合、`spend_usd`、`licensed_seats`、`cost_per_active_user` がnullになり得ます。

---

## 12. tool risk tier の前提

`risk_tier` は、synthetic governance attribute（syntheticなガバナンス属性）です。

これは、synthetic access governance domain内のreview context（レビュー文脈）として使います。  
実在するvendorやtoolに対する客観的なproduct-safety assessment（製品安全性評価）として解釈すべきではありません。

v0.1.0では、`risk_tier` は次を支援するために使われます。

- review strictness（レビューの厳格さ）
- approval behavior（承認挙動）
- review routing（レビュー担当・経路の振り分け）
- review candidates のprioritization（優先順位付け）

### 含意

このdatasetにおけるhigh-risk toolとは、synthetic governance modelがより厳格なreviewを必要とするtoolとして扱っている、という意味です。  
実在する製品についての主張ではありません。

---

## 13. data classification の前提

`data_classification` は、requested use case（申請されたユースケース）で扱うことが想定されるdataの最大感度を表します。

対応する値は次の通りです。

- `public`
- `internal`
- `confidential`
- `restricted`

このclassificationは、synthetic request contextの一部として生成され、approval logic（承認ロジック）とreview logic（レビューロジック）で使用されます。

### 含意

`data_classification` は、単純化されたgovernance input（ガバナンス入力）として読むべきです。  
完全なenterprise data classification policy implementation（企業向けデータ分類ポリシーの実装）ではありません。

---

## 14. tool adoption modeling の前提

tool adoption は、productivity impact（生産性への影響）を直接測るものではなく、operational proxy（運用上の代理指標）として扱います。

このプロジェクトでは、adoptionを次のようなobservable warehouse signals（warehouse上で観測可能なシグナル）で評価します。

- approved users
- active users
- sessions
- prompts
- spend
- cost per active user

主要なmonthly adoption martは次です。

- `tool_adoption_monthly`

このmartは、approved-access stock、monthly usage flow、monthly spend flowを比較します。

### このプロジェクトにおけるadoptionの意味

このプロジェクトでは、tool adoption は、承認されたtool accessがteam-level usageとして観測可能になることを意味します。  
spendは、その文脈を補助するreview contextとして扱います。

### このプロジェクトでadoptionが意味しないもの

このプロジェクトでは、次を直接測定しません。

- productivity improvement
- feature-level proficiency
- user satisfaction
- task quality improvement
- toolによって生じたcost savings

これらを測るには、追加のproduct analytics、survey、workflow、business outcome data が必要であり、v0.1.0のスコープ外です。

---

## 15. business review signal の前提

一部のmodeled conditions（モデル化された条件）は、pipeline failure（パイプライン失敗）ではなく、期待されるanalytical outputs（分析出力）です。

例:

- usage exists without approved access
- approved access exists without recent usage
- usage exists without a billing row
- billing exists without usage
- high-priority review candidates exist

これらは次のようなmartsに表示されます。

- `governance_exceptions_current`
- `adoption_review_candidates_monthly`

spend-usage mismatch は、confirmed accounting error（確定した会計エラー）や confirmed billing error（確定した請求エラー）ではなく、review candidateとして解釈すべきです。

### 原則

Business exceptions are outputs. Transformation inconsistencies are failures.

つまり、business review candidatesはmartsに見える形で出力し、壊れた変換ロジックはdbt testsで失敗させるべきです。

---

## 16. mart modeling の前提

mart layer は business-facing（ビジネス向け）かつ denormalized（非正規化された）です。

主要なmartsは次の通りです。

| Mart | 目的 |
|---|---|
| `access_requests_monthly` | monthly request inflow、approval/rejection decision flow、month-end backlogを要約する |
| `tool_adoption_monthly` | approved-access stock、monthly usage flow、monthly spend flowを比較する |
| `adoption_review_candidates_monthly` | approval、usage、spend のalignment statesをreview candidatesに分類する |
| `governance_exceptions_current` | current approved access と recent 30-day usage をuser-tool grainで比較する |

martsはreviewとanalysisを支援するためのものです。  
historical organizational state の audit-grade reconstruction（監査レベルの履歴再構築）ではありません。

特に、`adoption_review_candidates_monthly` は definitive root-cause diagnosis layer（確定的な根本原因診断レイヤー）ではなく、reviewer-facing follow-up surface（レビュー担当者向けの確認面）として解釈すべきです。

### 16.1 martの粒度と指標の解釈

mart層では、異なるビジネス上の問いに対応できるよう、意図的に複数の粒度を持つ分析用データセットを提供しています。

`tool_adoption_monthly` は、月次のチーム・ツール単位の分析を目的として設計されています。このmartの粒度は「1行が1つの reporting month、team、tool を表す」単位です。そのため、`approved_users_total` や `active_users_total` などの指標は、この行粒度の範囲内で解釈する必要があります。

例えば、最新の reporting month に対して `approved_users_total` を合計すると、その値は最新月におけるチーム・ツール行ごとの approved-user count の合計になります。これは global distinct user count、つまり全体で重複排除した一意のユーザー数として解釈してはいけません。同じユーザーが複数のツールに対して approved access を持つ場合、そのユーザーは複数の team-tool row に寄与し得るためです。

これは意図的なモデリング上のトレードオフです。このmartは、チーム・ツール単位で adoption、usage、spend の整合性を見ることに最適化されており、全体の user-level deduplication を目的としているわけではありません。

user-level の解釈が必要な場合、report script が下位レイヤーのモデルを直接読みに行くのではなく、warehouse 側で user-level mart を公開または拡張するべきです。例えば、以下のような選択肢があります。

- `governance_exceptions_current` は、approval と recent usage exception review のための current user-tool surface をすでに提供しています。
- 将来的に `user_tool_adoption_monthly` mart を追加すれば、「1行が1つの reporting month、user、tool を表す」粒度で、月次の user-level adoption analysis を行えます。
- 将来的に `user_adoption_monthly` mart を追加すれば、「1行が1つの reporting month と user を表す」粒度で、user-level tool portfolio analysis を行えます。

この方針により、report layer は business-facing marts の consumer としての役割を保ちつつ、粒度ごとの business semantics は dbt models の中に閉じ込めることができます。

---

## 17. stock and flow metric の前提

このプロジェクトでは、一部のmartでstock metrics（ストック指標）とflow metrics（フロー指標）を意図的に組み合わせます。

### flow metrics

flow metricsは、reporting period（報告期間）中のactivityを表します。

例:

- `requests_total`
- `approvals_total`
- `rejections_total`
- `active_users_total`
- `total_sessions`
- `total_prompts`
- `spend_usd`

### stock metrics

stock metricsは、ある時点のstate（状態）を表します。

例:

- `pending_total`
- `approved_users_total`

### 重要な区別

`spend_usd` は、reporting month（報告月）に認識されたspendを表すため、monthly flow-like measure（月次のflowに近い指標）として扱います。  
ただし、これはdaily activity eventsではなく、monthly billing rowsに由来します。

`pending_total` は month-end backlog stock metric（月末時点のbacklogを表すstock指標）です。  
reporting month中に提出されたpending requestsの数ではありません。

`approved_users_total` は month-end approved-access stock metric（月末時点のapproved accessを表すstock指標）です。  
reporting month end時点でapproved accessを持つusersをカウントします。

---

## 18. reporting spine の前提

一部のmartでは、metric sourcesをjoinする前に reporting spine を定義します。

reporting spine とは、あるmetric sourceが存在しない場合でも、martに表示すべきreporting keysの集合です。

例えば、`tool_adoption_monthly` は approval、usage、spend を比較します。  
approvalまたはusageが存在すれば、spend rowが存在しない場合でも、そのrowはmartに存在し得ます。

### 含意

metric sourcesをreporting spineにjoinした後は、次のように扱います。

- 存在しないcount metricsは `0` として表現される場合がある
- 存在しないboolean flagsは `false` として表現される場合がある
- ratio metricsは未定義の場合に `NULL` のままになる場合がある
- billing rowが存在しない場合、spend fieldsは `NULL` のままになる場合がある

このプロジェクトでは、mart上のnull spend fieldは、billing rowがreporting spineにjoinされなかったことを意味する場合があります。  
これは自動的にzero spendとして解釈すべきではありません。

---

## 19. time and date の前提

このプロジェクトは、固定されたgenerated time window（生成済み時間範囲）を使用します。

generated dataset は12か月分のsynthetic activityを含みます。  
これにより、month-based comparisons（月次比較）の再現性が保たれ、recent-window logicがreviewerのlocal実行日に依存しなくなります。

一般的なtemporal assumptions（時間に関する前提）は次の通りです。

- timestamps はdownstreamのUTC(Coordinated Universal Time:協定世界時)ベースのlogic向けに正規化される
- month fields は月の最初のcalendar dayを表す
- recent usage は利用可能な最大 `usage_date` を基準にする
- generated data はlocal system clockに依存すべきではない

### 含意

このプロジェクトは、再現可能なlocal validationを目的としています。  
同じgenerated inputsで再実行した場合、同じ分析上の解釈が保たれるべきです。

---

## 20. natural key の前提

このプロジェクトでは、v0.1.0において natural business keys（自然な業務キー）を使用します。

例:

- `tool_code`
- `user_id`
- `request_id`

v0.1.0では surrogate keys（代理キー）は導入していません。

これは、synthetic domainが安定したgenerated identifiersを持ち、スコープも小さいための意図的な単純化です。

### 含意

将来、複数source systems、late-arriving records（遅れて到着するレコード）、production-like slowly changing dimensionsへ拡張する場合は、surrogate key strategyを見直す必要があります。

---

## 21. relationship の前提

foreign key-like relationships は、解決可能なnatural keysを通じてモデル化します。

例:

- request requester → user
- request tool → tool
- usage user → user
- usage tool → tool
- spend tool → tool
- request reviewer → user（reviewerが存在する場合）

dbt testsでは、これらをrelationship checksとして検証します。

### 重要な解釈

relationship check は、key value が参照先モデルに解決できることを確認します。  
これは、テスト対象モデルが参照先モデルから構築されたことを意味しません。

例えば、fact modelは `tool_code` を持ち、それを `dim_tool.tool_code` に対してテストできます。  
これにより、downstream joinsが安全であることを確認できます。

---

## 22. synthetic data の前提

このdatasetは synthetic かつ deterministic です。

warehouse modeling の観点では、raw data は controlled analytical fixture（制御された分析用fixture）として解釈すべきです。  
raw dataは、dbt modeling、testing、documentation、report generationを支えるために、安定し、検査可能で、再現可能であるように設計されています。

requests、approvals、usage、spend は意図的に相関を持たせています。  
完全に独立したランダムテーブルとしては扱っていません。

### 含意

このdatasetはproduction dataではなく、実在するenterprise AI tool usageについて主張するものではありません。  
downstream warehouseに対して、十分に現実味のあるinput boundaryを提供するためのものです。

---

## 23. スコープ外のモデリング（Out-of-Scope Modeling）

次の内容は、v0.1.0のスコープ外です。

- production orchestration（本番用オーケストレーション）
- live extraction（ライブデータ抽出）
- cloud warehouse deployment（クラウドウェアハウスへのデプロイ）
- application UI（アプリケーションUI）
- real access provisioning（実際のアクセス付与）
- real audit trails（実際の監査証跡）
- slowly changing user dimensions（履歴付きユーザーディメンション）
- access revocation（アクセス剥奪）
- feature-level product telemetry（機能単位のプロダクト利用計測）
- productivity impact measurement（生産性影響の測定）
- incident management（インシデント管理）
- alerting（アラート通知）
- production observability（本番運用向けオブザーバビリティ）
- audit-grade historical reconstruction（監査レベルの履歴再構築）

これらは意図的に除外しています。  
これにより、このプロジェクトは最小限で確認しやすいdbt warehouseに焦点を保っています。

---

## 24. 将来のモデリング拡張（Future Modeling Extensions）

将来的にwarehouse modelingのスコープを広げる場合、追加のupstream dataやsource contract変更を伴う可能性がある拡張候補として、次のようなものが考えられます。

- historical organization snapshots（履歴付き組織スナップショット）
- slowly changing dimensions（履歴付きディメンション）
- access revocation-aware approval stock modeling（アクセス剥奪を考慮した承認stockモデリング）
- license contract modeling（ライセンス契約モデリング）
- richer spend allocation models（より詳細な費用配賦モデル）
- feature-level usage telemetry modeling（機能単位の利用テレメトリモデリング）
- productivity or outcome metric marts（生産性または成果指標mart）
- production-style freshness checks（本番運用に近いfreshness checks）
- orchestration metadata integration（オーケストレーションメタデータ統合）
- dashboard or BI layer integration（ダッシュボードまたはBI(Business Intelligence:ビジネスインテリジェンス)層との統合）

これらの拡張はv0.1.0では必須ではありません。  
また、現在のGeneratorを拡張する予定を示すものではありません。  
ただし、このプロジェクトをminimal portfolio warehouseの範囲を超えて拡張する場合には、自然な検討候補になります。

---

## 25. まとめ

`access-governance-warehouse` v0.1.0 は、deterministic synthetic data と layered dbt warehouse を使って、単純化した access governance domain をモデル化します。

主な前提は次の通りです。

- usersはcurrent-state onlyとしてモデル化する
- access requestsはfinal-state request rowsとして扱う
- 各 dbt model には、1行が何を表すかを定義する明示的な粒度（grain）がある
- usageはevent-levelではなくdaily aggregatedである
- spendはmonthly team-tool billing dataである
- revocationをモデル化していないため、approvalは持続する
- recent usageはsystem clockではなくgenerated datasetを基準にする
- adoptionはapproval、usage、spendに基づくoperational proxyである
- business review signalsはanalytical outputsであり、test failuresではない

これらの前提により、このプロジェクトは最小限で、再現可能で、確認しやすい構成を保ちながら、analytics engineeringとウェアハウスモデリングの実践を信頼できる形で示せるようになっています。
