# テスト戦略

このドキュメントは、`access-governance-warehouse` v0.1.0 のテスト戦略を説明するものです。

このプロジェクトでは、dbt (data build tool) のデータテスト（data tests）を使用して、source contract（ソース契約）、staging層での正規化、ディメンション整合性、ファクトの粒度、intermediate層のstock/flow不変条件、mart層での照合、レビュー候補の分類ロジックを検証します。

このテスト戦略では、意図的に次の2つを分けています。

1. 変換処理の正しさ（transformation correctness）  
   変換処理が壊れている場合に dbt test failure として扱うべきもの
2. ビジネスレビューシグナル（business review signals）  
   パイプライン失敗（pipeline failure）ではなく、分析出力としてmartに表示すべきもの

---

## 1. テストの目的

このテストスイートは、ウェアハウスを信頼でき、説明可能で、レビュアーが確認しやすい状態にすることを目的としています。

主な目的は次の通りです。

- raw source contract が構造的に利用可能であることを検証する
- stagingモデルがsourceの粒度を保ち、低レベルのフィールドを正しく正規化していることを確認する
- 再利用可能なディメンションキーを保護する
- ファクトテーブルの粒度と指標（metric）の妥当性を保護する
- martで使われるintermediate層のstock/flowロジックを検証する
- martの指標を上流モデルと照合する
- レビュー候補の分類が論理的に一貫していることを確認する
- 正確なsynthetic row countに依存する壊れやすいテストを避ける

このプロジェクトは、local warehouse かつ analytics engineering portfolio project です。  
そのため、このテストスイートは本番規模の監視ではなく、検査可能な正しさ（inspectable correctness）と再現可能な検証（reproducible validation）を重視します。  
本番運用向けのオブザーバビリティ、アラート通知、インシデント管理は v0.1.0 のスコープ外です。

---

## 2. テスト方針

### 2.1 dbt test failure にすべきもの

dbtテストは、変換パイプラインが構造的または論理的に壊れている場合に失敗すべきです。

例:

- 必須keyが欠けている
- 宣言された粒度で重複行がある
- enum-like values（列挙型に近い値）に想定外の値がある
- foreign key-like relationships（外部キーに近い関係）が壊れている
- count metric や spend metric が負になっている
- boolean helper flags に一貫性がない
- 上流layerと下流layerの照合が壊れている
- `review_status`, `review_owner_hint`, `review_priority` のロジックが誤っている

これらの失敗は、ウェアハウス出力が信頼できない状態になっていることを示します。

### 2.2 dbt test failure にすべきではないもの

ビジネスレビューシグナルは、それ自体を dbt test failure にすべきではありません。

例:

- `finance_review_active_without_billing` に分類された行
- `cost_review_billed_without_usage` に分類された行
- `adoption_review_approved_not_used` に分類された行
- high-priority review candidates
- generator tuning 後に `aligned` rows の数が変化すること

これらの行は分析出力です。  
これらは関係者が確認すべき状態を示しますが、変換上の欠陥（transformation defect）ではありません。

例えば、usage は存在するが billing row が存在しない行は、finance/procurement 向けの有効なレビュー候補である可能性があります。  
そのような行は `adoption_review_candidates_monthly` に表示すべきであり、failed dbt test として扱うべきではありません。

---

## 3. テストカテゴリ

このプロジェクトでは、dbtのデータテストを大きく2種類に分けて使います。

1. 汎用テスト（generic tests）
2. 単独SQLテスト（singular tests）

### 3.1 汎用テスト（Generic tests）

汎用テストは YAMLファイルに宣言し、一般的な構造チェックに使用します。

このプロジェクトでは、次の generic test patterns を使用します。

- `not_null`
- `unique`
- `relationships`
- `accepted_values`

汎用テストは、検証内容がカラム単位である場合や、一般的な dbt testing pattern に合う場合に使用します。

例:

- primary business keys が null ではない
- primary business keys が unique である
- enum-like fields が accepted values のみを含む
- foreign key-like identifiers が想定される上流dimensionまたはsource tableに解決できる
- required metric columns に値が入っている

このプロジェクトでは、`relationships` tests は参照解決可能性のチェック（resolvability checks）として解釈します。  
つまり、foreign key-like value が参照先のsourceまたはdimensionにjoinできることを確認します。  
これは、テスト対象のモデルが参照先モデルから構築されたことを意味しません。

このプロジェクトでは、汎用テストの設定に dbt の `arguments:` style を使用します。

例:

```yaml
data_tests:
  - accepted_values:
      arguments:
        values:
          - low
          - medium
          - high
```

Block-style YAML lists は、可読性とGit diffの見やすさのために優先します。

### 3.2 単独SQLテスト（Singular tests）

単独SQLテストは `tests/singular/` 配下の SQLファイルです。

検証内容が custom SQL logic、cross-column logic、reconciliation、または grain-level validation を必要とし、クエリとして書いた方が明確な場合に使用します。

例:

- composite grain uniqueness
- 複数カラムにまたがる non-negative metric checks
- spend component reconciliation
- monthly usage reconciliation
- approved-access stock monotonicity
- mart-level row-count または metric reconciliation
- review-candidate routing and priority consistency

単独SQLテストは、検証が通る場合に0行を返すべきです。

---

## 4. layer別のテスト範囲（Layer-Level Coverage）

このテストスイートは、warehouse layer structure に沿っています。

```text
raw sources
  -> staging
  -> core
  -> intermediate
  -> marts
```

各layerは異なるテスト上の責務を持ちます。

---

## 5. source層のテスト（Source Tests）

source層のテストは raw input contract を検証します。

対象ファイル:

```text
models/sources/sources.yml
```

実行コマンド:

```bash
uv run dbt test --select "source:access_governance,test_type:generic"
```

source層のテストは次を検証します。

- raw primary keys が適切に存在し、必要な場合に unique である
- raw enum-like values が accepted sets に含まれている
- raw user / tool references が source tables に解決できる
- nullable review-side fields が誤って `not_null` としてテストされていない

source層は、このプロジェクト用に生成された deterministic synthetic raw Parquet files を表します。  
source層のテストは dbt に公開される raw contract を検証しますが、generator implementation detail のすべてを検証するものではありません。

generator側のQAは、決定論的な出力、rawファイルの存在、rawカラム順序の一致、行数の観測可能性、generator固有のビジネスルール実現を検証します。

---

## 6. staging層のテスト（Staging Tests）

staging層のテストは、sourceに沿った整形・標準化（source-conformed cleanup）を検証します。

対象ファイル:

```text
models/staging/access_governance/schema.yml
```

実行コマンド:

```bash
uv run dbt test --select "path:models/staging/access_governance,test_type:generic"
```

staging層のテストは次を検証します。

- staging keys が保持されている
- normalized enum-like values が有効なままである
- helper boolean columns に値が入っている
- required staging metrics が null ではない
- nullable review-side fields が意図通り nullable のままである

staging層は join や aggregation を行いません。  
そのテストは、raw grainを保ちながら、names、types、timestamps、simple helper fields を正規化することに焦点を当てます。

---

## 7. core層のテスト（Core Tests）

core層のテストは、再利用可能なdimensionsとfactsを検証します。

対象ファイル:

```text
models/core/schema.yml
```

実行コマンド:

```bash
uv run dbt test --select "path:models/core,test_type:generic"
```

core層の汎用テストは次を検証します。

- `dim_tool.tool_code` が not null かつ unique である
- `dim_user.user_id` が not null かつ unique である
- `dim_user.user_email` が unique である
- `fct_access_request.request_id` が not null かつ unique である
- core fact keys が再利用可能なdimensionsに解決できる
- core enum-like values が有効なままである

core層の単独SQLテストは次を検証します。

- final request statuses が期待される review-side fields を持つ
- approval lead time が非負である
- usage fact grain が一意である
- usage metrics が非負である
- spend fact grain が一意である
- spend metrics が非負である
- spend components が total spend と整合する

coreモデルは再利用可能な warehouse semantics を定義します。  
そのため、テストは dimensional keys、fact grains、metric validity、relationship integrity に焦点を当てます。

---

## 8. intermediate層のテスト（Intermediate Tests）

intermediate層のテストは re-graining、stock logic、再利用可能な mart support logic を検証します。

対象ファイル:

```text
models/intermediate/governance/schema.yml
```

実行コマンド:

```bash
uv run dbt test --select "path:models/intermediate/governance,test_type:generic"
```

単独SQLテスト:

```bash
uv run dbt test --select "path:tests/singular/intermediate,test_type:singular"
```

intermediate層には、次の目的特化モデルがあります。

- current approved-access state
- recent 30-day usage state
- month-end open request backlog
- approved-access stock as of month end
- monthly usage aggregated to team and tool

intermediate層のテストは次を検証します。

- 宣言されたgrainが一意である
- required keys に値が入っている
- user / tool references が正しく解決できる
- helper flags が論理的に一貫している
- recent 30-day windows が有効である
- open request rows が本当に month-end backlog を表している
- approved-access rows が month end 時点で有効である
- revocation（アクセス剥奪）がモデル化されていない間、approved-access stock が単調非減少である
- monthly usage totals が daily usage facts と照合できる

intermediate層は business-facing output layer ではありません。  
その目的は、再利用可能な state、windowing、stock、aggregation logic を切り出し、mart SQLを読みやすく保つことです。

---

## 9. mart層のテスト（Mart Tests）

mart層のテストは business-facing analytical outputs を検証します。

対象ファイル:

```text
models/marts/governance/schema.yml
```

実行コマンド:

```bash
uv run dbt test --select "path:models/marts/governance,test_type:generic"
```

単独SQLテスト:

```bash
uv run dbt test --select "path:tests/singular/marts,test_type:singular"
```

mart層には次のモデルが含まれます。

- `access_requests_monthly`
- `tool_adoption_monthly`
- `adoption_review_candidates_monthly`
- `governance_exceptions_current`

mart層のテストは次を検証します。

- mart grains が一意である
- required reporting fields に値が入っている
- request metrics が非負である
- usage metrics が upstream monthly usage aggregation と照合できる
- spend metrics が spend fact と照合できる
- approved-user stock が approved-access intermediate model と照合できる
- backlog totals が month-end open request intermediate model と照合できる
- exception flags が論理的に一貫している
- review candidate classifications が論理的に一貫している
- review owner hints が論理的に一貫している
- review priorities が論理的に一貫している

mart層のテストは、正当なreview signalsを抑え込むことなく、business-facing outputs の正しさを検証するように設計されています。

---

## 10. ビジネスレビューシグナルとテスト失敗（Business Review Signals vs Test Failures）

このプロジェクトでは、分析上の検出結果（analytical findings）とデータ変換上の失敗（data transformation failures）を意図的に区別します。

### 10.1 分析上の検出結果（Analytical findings）

次の条件は、有効な business review signals です。

- usage exists without approved access
- approved access exists without recent usage
- usage exists without a billing row
- billing exists without usage
- a high-risk tool appears in a high-priority review candidate row

これらは、承認・利用・請求の状態が期待通りに揃っていないことを示すレビュー対象です。

これらは次のようなmartに現れることが期待されます。

- `governance_exceptions_current`
- `adoption_review_candidates_monthly`

これらは関係者によってreviewされるべきですが、その存在はdbt pipelineが壊れていることを意味しません。

### 10.2 変換上の失敗（Transformation failures）

次の条件はtest failureにすべきです。

- 宣言されたgrainで重複行がある
- invalid `review_status` values
- invalid `review_priority` values
- required keys が欠けている
- negative metrics
- source-to-staging または fact-to-dimension relationships が壊れている
- mart metrics と upstream models の reconciliation mismatch
- `review_status` value が、それを導出するpresence flagsと一致しない

このドキュメントでは、business exception とは、必ずしもdata defectではなく、関係者によってreviewされるべき条件を意味します。

原則は次の通りです。

```text
Business exceptions are outputs.
Transformation inconsistencies are failures.
```

---

## 11. 壊れやすいRow-Count Testsを避ける

synthetic generator のパラメータは将来調整される可能性があります。

例えば、billed spend rows の数は、spend-generation parameters が調整された場合に変わる可能性があります。  
そのcountがstable source contractの一部でない限り、testsはgenerator-dependent row countsをhard-codeすべきではありません。

避けるべきテスト例:

```text
raw_tool_spend_monthly row count = 313
aligned row count = 313
finance_review_active_without_billing row count = 28
```

代わりに、次のようなreconciliation testsを優先します。

```text
mart rows with spend_usd is not null
=
fct_tool_spend_monthly rows
```

または:

```text
mart metric total
=
upstream metric total
```

これにより、synthetic generator を意図的に調整してもテストが壊れにくくなり、同時に変換処理の正しさを検証できます。

---

## 12. 検証ベースライン（Validation Baseline）

現在の v0.1.0 validation baseline では、テストスイートは次の構成です。

| Test category | Count |
|---|---:|
| Generic tests | 278 |
| Core singular tests | 7 |
| Intermediate singular tests | 12 |
| Mart singular tests | 18 |
| Total data tests | 315 |

現在の validation baseline は次のobjectを対象にします。

| Object type | Count |
|---|---:|
| View models | 15 |
| Table models | 4 |
| Data tests | 315 |

現在の baseline build は、15個のview models、4個のtable models、315個のdata testsを含む合計334ノードでpassします。

---

## 13. 推奨コマンド

### プロジェクトをparseする

```bash
uv run dbt parse
```

### full buildを実行する

`dbt build` は、models と tests を dependency order に従って一緒に実行するため、end-to-end validation 用の推奨commandです。

```bash
uv run dbt build
```

### すべてのテストを実行する

```bash
uv run dbt test
```

### 汎用テストのみ実行する

```bash
uv run dbt test --select "test_type:generic"
```

### 単独SQLテストのみ実行する

```bash
uv run dbt test --select "test_type:singular"
```

### source層の汎用テストを実行する

```bash
uv run dbt test --select "source:access_governance,test_type:generic"
```

### layer別の汎用テストを実行する

```bash
uv run dbt test --select "path:models/staging/access_governance,test_type:generic"
uv run dbt test --select "path:models/core,test_type:generic"
uv run dbt test --select "path:models/intermediate/governance,test_type:generic"
uv run dbt test --select "path:models/marts/governance,test_type:generic"
```

### layer別の単独SQLテストを実行する

```bash
uv run dbt test --select "path:tests/singular/core,test_type:singular"
uv run dbt test --select "path:tests/singular/intermediate,test_type:singular"
uv run dbt test --select "path:tests/singular/marts,test_type:singular"
```

### dbt documentationを生成する

```bash
uv run dbt docs generate
uv run dbt docs serve
```

---

## 14. テスト失敗の確認方法（Test Failure）

dbt test が失敗した場合は、次の3つの観点で確認します。

### 14.1 構造上の失敗か？

例:

- key が重複している
- 必須keyが null になっている
- 想定外の enum value が含まれている
- `relationships` test が失敗している

これらは通常、source contract（ソース契約）の問題、変換処理の問題、またはテスト定義の問題を示します。

### 14.2 照合の不一致か？

例:

- martの合計値が上流のfactの合計値と一致しない
- spend component の合計が `spend_usd` と一致しない
- 月次集計結果が日次factと照合できない

これらは通常、変換ロジックのバグ、または上流モデルの粒度に関する前提が変わったことを示します。

### 14.3 実際にはビジネスレビューシグナルではないか？

例:

- 利用はあるが請求がない
- 承認はあるが利用がない
- 請求はあるが利用がない

これらは通常、martに表示すべき分析結果であり、失敗するテストとして実装すべきではありません。

ビジネスレビューシグナルが失敗するテストとして現れた場合は、まずそのテストが本当に変換処理の正しさを保護しているかを確認します。  
もしそのテストが、有効なレビュー候補がmartに現れることを妨げているだけであれば、そのテストは修正または削除すべきです。

---

## 15. 将来の保守メモ

### 15.1 revocation（アクセス剥奪）を導入する場合

approved access が持続することを前提とするテストを見直します。

特に、access revocation をモデル化する場合、approved-access stock は正当に減少し得ます。  
現在、approved-access stock が単調非減少であることを期待しているテストは修正する必要があります。

### 15.2 historical organization snapshots（履歴付き組織スナップショット）を導入する場合

current-state user attribution（現在状態のユーザー紐づけ）に依存するモデルとテストを見直します。

影響を受ける可能性がある領域:

- request attribution（requestの組織紐づけ）
- usage attribution（usageの組織紐づけ）
- team別のapproved-user stock
- monthly adoption marts

### 15.3 warehouse backend を変更する場合

プロジェクトをDuckDB以外のbackendへ移行する場合、decimal や ratio metric に関する厳密な等価比較を見直します。

影響を受ける可能性がある領域:

- spend component reconciliation（spend構成要素の照合）
- cost-per-active-user consistency（active userあたりcostの整合性）
- rounded monetary comparisons（金額丸め後の比較）

### 15.4 generator parameters を調整する場合

偶発的な synthetic row count に依存するテストを追加しないようにします。

次のような検証を優先します。

- grain validation（粒度の検証）
- relationship validation（参照関係の検証）
- enum validation（列挙値の検証）
- metric non-negativity（指標が非負であることの検証）
- upstream/downstream reconciliation（上流・下流間の照合）
- classification logic validation（分類ロジックの検証）

---

## 16. まとめ

このテストスイートは、ウェアハウスの変換パイプラインが構造的に健全であり、分析上も一貫していることを検証します。

このテストスイートは、次を保護するように設計されています。

- source contract（ソース契約）
- staging層での正規化
- core層のディメンション整合性
- factの粒度
- intermediate層のstock/flow不変条件
- mart層での照合
- レビュー候補の分類ロジック

同時に、このテストスイートは、ビジネスレビュー候補がmartに現れることを意図的に許容します。  
これらのレビュー候補は、このプロジェクトの分析価値の一部であり、テスト失敗ではありません。
