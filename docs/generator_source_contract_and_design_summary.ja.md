# Generator Source Contract and Design Summary

## 1. 目的

この文書は、`access-governance-warehouse` v0.1.0 で使用する synthetic rawデータジェネレーターの contract-level summary をまとめたものです。

これは Generator の完全な仕様書ではありません。  
ここでの目的は、次の点を簡潔に示すことです。

- Generator が何を出力するのか
- 出力される raw layer がどのような構造的保証を持つ想定なのか
- どのような決定論的・重み付き生成ルールが dataset を形作っているのか
- v0.1.0 において、どこまでを扱い、どこを意図的に省略しているのか
- 出力された raw layer が、下流の DuckDB + dbt warehouse をどのように支えるのか

この Generator は、このリポジトリにおける補助コンポーネントです。  
役割は、決定論的で確認しやすく、warehouse でそのまま扱える raw source layer を提供することです。

この raw layer は、著者が別プロジェクトで作成した SaaS-like な社内向け AI tool access request / approval application に蓄積されうる source data を近似することを意図しています。

## 2. このリポジトリにおける位置づけ

このリポジトリにおいて、レビューア向けの主な価値は下流の warehouse 実装にあります。

- source definitions
- staging models
- dimensions and facts
- marts
- tests
- dbt docs
- static governance reporting

したがって、この Generator は warehouse layer のための raw source-contract provider として扱うのが適切であり、主役となるポートフォリオ成果物ではありません。

## 3. 成果物

v0.1.0 において、この Generator は `data/raw/` 配下にちょうど 5 つの raw Parquetファイルを出力します。

- `raw_tool_catalog.parquet`
- `raw_user_directory.parquet`
- `raw_access_requests.parquet`
- `raw_usage_events_daily.parquet`
- `raw_tool_spend_monthly.parquet`

これらのファイルが、Generator の主要な成果物です。

`data/warehouse/access_governance.duckdb` にあるローカル DuckDBファイルは、SQL および dbt 実行のための下流 warehouse 用アーティファクトです。これは Generator の成果物ではありません。

## 4. Raw source contract

### 4.1 定義される粒度

出力される raw layer は、次のテーブル粒度を保ちます。

- `raw_tool_catalog`: 1 tool あたり 1 row
- `raw_user_directory`: 1 user あたり 1 row
- `raw_access_requests`: 1 access request あたり 1 row
- `raw_usage_events_daily`: user × tool × day あたり 1 row
- `raw_tool_spend_monthly`: month × team × tool あたり 1 row

これらの粒度は source contract の一部であり、実装上の任意事項ではありません。

### 4.2 デフォルト v0.1.0 の目標行数

default の v0.1.0 setup では、Generator は次の目標行数を前提に構成されています。

- `raw_tool_catalog`: 5
- `raw_user_directory`: 198
- `raw_access_requests`: 553
- `raw_usage_events_daily`: 30000
- `raw_tool_spend_monthly`: 313

これらの目標は、default のローカル実行設定におけるデータセット構成の一部です。  
実際の出力はこれらの目標に概ね整合することを想定しており、必要に応じて、generator design で定義された acceptance ranges が適用されます。

### 4.3 構造的保証

この Generator は、raw layer において次の保証を保つことを意図しています。

- 決定論的な行順
- 規定の列順
- 解決可能なテーブル間参照
- raw粒度での一意性
- status に応じた NULL 許容
- 非負の count-like metrics
- UTC の timestamp 生成
- month field を月初日にそろえること
- USD monetary values を小数第 2 位まで量子化すること
- requester / reviewer / usage の eligibility における inactive user の除外（該当箇所）

## 5. 再現性モデル

この Generator は、次の性質を持つように設計されています。

- 決定論的
- 確認しやすい
- 再現可能
- 業務ルール駆動
- ローカルで実行可能

v0.1.0 では、再現性は次の固定設定により担保されます。

- fixed seed: `18790314`
- fixed anchor month: `2025-12-01`
- fixed reporting window: 12 months

この Generator は、実行時のシステムクロックによって出力内容を変化させません。

### 5.1 再実行時の挙動

Generator は実行のたびに raw Parquet files を書き直すため、生成される論理的な表データが変わっていない場合でも、ファイルの更新日時は変わることがあります。

このリポジトリに現在コミットされている generator configuration を前提とし、同じ seed、同じ実装、同じ依存環境で実行する場合、期待される契約は、論理的な出力が安定していることです。

再現性を確認する場合、ファイルの更新日時をデータ変更の証拠として扱うべきではありません。代わりに、canonical logical export または validation artifacts を比較することを推奨します。

たとえば、`raw_access_requests` は、同じ生成条件で繰り返し canonical CSV export を行った結果、同じ SHA-256 hash を生成しました。

```text
74be333534f543785057bbbe656406f9fc59592a4b7617e551ee5760581d4fea
```

generator configuration を意図的に変更した場合は、論理的な出力が変わることが期待されます。その場合は、新しい generated dataset baseline として扱うべきです。

## 6. 生成モデル

この Generator は、制約のないランダム生成ではなく、ルールベースで動作します。

規範的な生成順序は次のとおりです。

1. entity setup
2. request volume
3. request context
4. review outcome
5. usage
6. spend

この順序を採用しているのは、下流 warehouse において、requests, approvals, usage, spend の間により一貫した関係構造を持たせるためです。

## 7. 重み付き・条件付き生成ポリシー

v0.1.0 の Generator は、完全に独立した row-wise random sampling ではなく、決定論的な weighted allocation と normalized conditional generation を用います。

この方針は意図的なものです。  
固定 seed と設定のもとで再現性を保ちながら、request workflow, observed usage, spend の間に、より解釈しやすい関係を持たせます。

### 7.1 Request generation

request generation は、まず件数を確定し、その後に行内容を埋める方式を取ります。

contract-level では、request rows は次の手順で構成されます。

1. annual team request targets を固定する
2. seasonality weights を用いて、それらを month に配分する
3. team × tool weights を用いて、month × team counts を tool に配分する
4. 得られた exact counts を deterministic な request-row skeletons に展開する
5. その skeletons に request context と review outcome を付与する

件数配分の形は、次のように要約できます。

```math
N_{m,t,k} \;\propto\; R_t \cdot s_m \cdot p_{t,k}
\qquad (1)
```

where

- $N_{m,t,k}$: month $m$, team $t$, tool $k$ に割り当てられた request count
- $R_t$: team $t$ の annual request target
- $s_m$: month $m$ の seasonality weight
- $p_{t,k}$: team $t$ と tool $k$ に対する team × tool request propensity

重み付き配分の後、最終的な request totals が設定値に整合するよう、整数行数は決定論的に補正されます。

review outcome も一様ではなく、重み付きで生成されます。  
reviewed subset の中では、approval likelihood は request context と tool risk に条件づけられます。

```math
P(\mathrm{approve}\mid \mathrm{reviewed}, p, c, r)
=
b_p \, m_c \, n_r
\qquad (2)
```

where

- $P(\mathrm{approve}\mid \mathrm{reviewed}, p, c, r)$: request が reviewed であることを条件とした approval probability
- $p$: `request_purpose`
- $c$: `data_classification`
- $r$: `risk_tier`
- $b_p$: purpose-specific base approval probability
- $m_c$: classification-specific approval multiplier
- $n_r$: risk-tier approval multiplier

pending は、単純な第三の status として一様抽選されるわけではありません。  
代わりに、pending backlog は month-end stock として別管理され、reviewed outcomes はこの weighted approval model によって形作られます。

### 7.2 Usage generation

usage generation は、request workflow から独立にサンプリングされるのではなく、最終的な request outcomes から導かれます。

contract-level では、Generator はまず、次のような current-state user-tool sets を導出します。

- approved-current pairs
- recent usage を持つ approved-active pairs
- recent usage を持たない approved-current pairs
- `used_without_approval` を表す controlled anomaly pairs

ここでいう “without recent usage” は pair の activity state を指しており、inactive users を意味するものではありません。  
inactive users は、usage rows の出力対象から引き続き除外されます。

つまり、出力される usage layer は approval state と相関を持つよう設計されつつ、限定的な例外面も持つ構造になっています。

daily grain では、usage_date の決定は一様な日付割り当てではなく、eligible calendar dates に対する weighted selection に従います。  
この選択ルールは、次のように要約できます。

```math
S^{\mathrm{usage\_date}}_{i,m,d}
=
\alpha_{w(d)}
\,
\beta_{b(d,m)}
\,
\varepsilon_{i,m,d}
\qquad (3)
```

where

- $S^{\mathrm{usage\_date}}_{i,m,d}$: pair-month-date candidate $(i,m,d)$ に対する date-selection score
- $i$: user-tool pair
- $m$: reporting month
- $d$: candidate calendar date
- $w(d)$: date $d$ の weekday
- $b(d,m)$: month $m$ 内における date $d$ の month-position bucket
- $\alpha_{w(d)}$: weekday multiplier
- $\beta_{b(d,m)}$: month-position multiplier
- $\varepsilon_{i,m,d}$: candidate $(i,m,d)$ に対する deterministic jitter

これらの scores は、独立な Bernoulli probability ではなく、selection weights として解釈されます。

通常の approved pairs については、approval-effective timing も eligible dates の制約として効くため、通常 usage が approval より前に現れることはありません。  
controlled anomaly pairs は、それとは別の bounded selection logic で扱われます。

### 7.3 Spend generation

spend generation は、request rows や usage rows から独立にサンプリングされるのではなく、billed month × team × tool states から構成されます。

contract-level では、spend realization は次の要素から成ります。

1. どの billed month × team × tool rows が存在するかを決める
2. contract activation timing を実現する
3. seat-related contract state を実現する
4. fixed / variable の spend components を導出する
5. total spend を計算し、monetary rounding を適用する

意図している contract-level relationship は、spend が seat state と observed usage の両方と相関することです。

spend-side composition は、次のように要約できます。

```math
\mathrm{spend\_usd}_{m,t,k}
=
\mathrm{fixed\_license\_cost\_usd}_{m,t,k}
+
\mathrm{variable\_usage\_cost\_usd}_{m,t,k}
\qquad (4)
```

where

- $`\mathrm{spend\_usd}_{m,t,k}`$: billing month $m$, team $t$, and tool $k$ における total spend
- $`\mathrm{fixed\_license\_cost\_usd}_{m,t,k}`$: fixed recurring license cost component
- $`\mathrm{variable\_usage\_cost\_usd}_{m,t,k}`$: usage-driven variable cost component

より抽象的な contract-level 表現では、variable component は usage intensity と seat-related billing state に依存することを意図しています。

```math
\mathrm{variable\_usage\_cost\_usd}_{m,t,k}
=
f\!\left(
U_{m,t,k},
L_{m,t,k}
\right)
\qquad (5)
```

where

- $U_{m,t,k}$: billing month $m$, team $t$, tool $k$ における usage intensity
- $L_{m,t,k}$: billing month $m$, team $t$, tool $k$ における seat-related または contract-related billing state
- $f(\cdot)$: configured spend model のもとでの deterministic cost-realization function

v0.1.0 では、monetary outputs は出力前に小数第 2 位まで量子化され、最終的な cross-table validation では次が成り立つことが求められます。

```math
\mathrm{spend\_usd}
=
\mathrm{fixed\_license\_cost\_usd}
+
\mathrm{variable\_usage\_cost\_usd}
\qquad (6)
```

これは、すべての emitted spend row に対して成り立つ必要があります。

### 7.4 Contract interpretation

この節は、Generator の weighted design を contract-level で要約したものとして読むべきです。

ここでは、すべての builder modules の実装詳細を再現することは意図していません。  
代わりに、生成ポリシーの大枠を記録しています。

- request rows は、weighted count planning と context-aware review rules によって割り当てられる
- usage rows は、approval-aware pair states と controlled anomalies から導かれる
- spend rows は、billed contract state と usage-correlated cost realization から導かれる

したがって、出力される raw layer は、意図的に、一様ランダム生成でも、テーブル間で完全に独立したものでもありません。  
これは、weighted business rules によって形作られた、決定論的な synthetic business dataset です。

## 8. 簡略化前提

v0.1.0 の source contract は、意図的に最小限の business model に制約されています。

主な簡略化前提は次のとおりです。

- user directory は current-state only である
- 組織履歴はモデル化しない
- access requests は、extract 時点での final workflow state を持つ request-level rows として表現する
- usage は event grain ではなく daily aggregated grain で表現する
- spend は monthly team × tool grain で表現する
- 下流 current-state logic のために approved-access persistence を仮定する
- revocation history は v0.1.0 ではモデル化しない

これらの前提は意図的なものです。  
raw layer をコンパクトで確認しやすくし、最小構成の warehouse portfolio に適したものに保つためです。

## 9. Validation boundary

Generator の出力は、書き込み前後の両方で validation されます。

この validation boundary には、次が含まれます。

- table-local QA
- cross-table QA
- schema-realization QA
- raw output existence checks
- validation artifact existence checks

canonical な validation artifacts は次のとおりです。

- `artifacts/validation/generator_validation_summary.md`
- `artifacts/validation/generator_validation_summary.json`

これらの artifacts は、出力された raw layer が意図した source contract を満たしていることを示す、主要な証拠として扱うべきです。

## 10. 確認支援

このリポジトリには、DuckDB 向けの確認用スクリプトも含まれています。

- `scripts/inspect_generated_raw_parquet.sql`

このスクリプトの役割は、生成された raw files を直接確認できるようにすることです。たとえば、次のような内容を確認できます。

- row counts
- schema
- preview rows
- distributions
- time ranges
- duplicate smoke checks
- spend-math smoke checks

このスクリプトは確認支援のためのものです。  
canonical な validation mechanism そのものではありません。

## 11. 下流 warehouse とのインターフェース

出力された raw layer は、下流の DuckDB + dbt warehouse に対する安定した upstream interface として機能することを意図しています。

特に、次を支えるように設計されています。

- 明示的な source definitions
- source-level tests
- 安定した upstream assumptions を持つ staging models
- dimension / fact の構築
- access governance business questions に答えるための marts
- lineage と documentation の確認

下流 warehouse は、たとえば次のような問いに答えることを意図しています。

- Which teams request, approve, or reject which tools over time?
- Are approved tools actually used?
- Which user-tool relationships show usage without approved access?
- Is spend directionally aligned with adoption and usage?

したがって、この Generator は end-user deliverable ではなく、warehouse modeling のための source-layer contract として理解するのが適切です。

## 12. 導線

軽量な Generator の概要は、次を参照してください。

- [`generator/README.ja.md`](../generator/README.ja.md)

リポジトリ全体の概要は、次を参照してください。

- [`README.ja.md`](../README.ja.md)
