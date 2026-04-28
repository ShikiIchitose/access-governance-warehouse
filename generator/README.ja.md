# Synthetic Raw Generator

このディレクトリには、`access-governance-warehouse` 向けの synthetic rawデータジェネレーターが含まれています。

この Generator は、このリポジトリにおける補助コンポーネントであり、主役となるポートフォリオ成果物ではありません。  
役割は、下流の DuckDB + dbt warehouseモデルが構築対象とできる、決定論的で確認しやすい rawデータセットを生成することです。

## この Generator を用意している理由

このプロジェクトの本体は、dbt を中心に据えたローカル warehouse のポートフォリオです。  
この Generator は、その warehouse 実装のために、安定したローカルの source contract を提供する目的で用意されています。

単なるランダムな表を作るのではなく、この Generator は access governance domain を想定した、ルールベースの synthetic business data を生成します。

1. entity setup
2. request volume
3. request context
4. review outcome
5. usage
6. spend

この因果的な順序を採用しているのは、下流の marts が、requests, approvals, adoption, exceptions, spend に関する現実的な business questions に答えられるようにするためです。

## 生成されるもの

この Generator は、`data/raw/` 配下に 5 つの raw Parquetファイルを出力します。

- `raw_tool_catalog.parquet`
- `raw_user_directory.parquet`
- `raw_access_requests.parquet`
- `raw_usage_events_daily.parquet`
- `raw_tool_spend_monthly.parquet`

これらの rawファイルが、Generator の実際の成果物です。

`data/warehouse/access_governance.duckdb` にあるローカル DuckDBファイルは、SQL や dbt の作業のための下流 warehouse 用アーティファクトです。これは Generator の主たる出力ではありません。

## 設計上の特徴

この Generator は、次の性質を持つように設計されています。

- 決定論的
- 確認しやすい
- 再現可能
- 業務ルール駆動
- ローカルで実行可能

v0.1.0 では、次の固定設定でデータセットを生成します。

- fixed seed: `18790314`
- fixed anchor month: `2025-12-01`
- reporting window: 12 months

実装では次を使っています。

- tabular assembly と最終的な rawテーブル構築には `pandas`
- slot realization, request assignment, duplicate-policy reconciliation, review routing のような決定論的な workflow 処理には、pure Python の stateful logic

## 出力仕様

raw layer は、各テーブルの粒度を明示的に保っています。

- `raw_tool_catalog`: 1 tool あたり 1 row
- `raw_user_directory`: 1 user あたり 1 row
- `raw_access_requests`: 1 access request あたり 1 row
- `raw_usage_events_daily`: user × tool × day あたり 1 row
- `raw_tool_spend_monthly`: month × team × tool あたり 1 row

default の v0.1.0 setup で想定している目標行数は次のとおりです。必要に応じて、下流の validation rules では文書化された acceptance ranges を使う場合があります。

- `raw_tool_catalog`: 5
- `raw_user_directory`: 198
- `raw_access_requests`: 553
- `raw_usage_events_daily`: 30000
- `raw_tool_spend_monthly`: 313

また、この Generator は raw contract の中核となる次のルールも守ります。

- 規定の列順
- 決定論的な行順
- 解決可能なテーブル間参照
- raw粒度での一意性
- status に応じた NULL 許容
- requester / reviewer / usage selection における inactive user の除外（該当箇所）

## 検証

Generator の出力は、書き込み前後の両方で検証されます。

この Generator では、次の観点で検証を行います。

- table-local QA
- cross-table QA
- schema-realization QA
- raw output existence checks
- validation artifact existence checks

検証アーティファクト:

- [`../artifacts/validation/generator_validation_summary.md`](../artifacts/validation/generator_validation_summary.md)
- [`../artifacts/validation/generator_validation_summary.json`](../artifacts/validation/generator_validation_summary.json)

これらのファイルは、Generator の出力品質を確認するための canonical な validation artifacts です。

## 実行方法

リポジトリルートから実行してください。

```bash
uv sync
uv run python -m scripts.generate_synthetic_raw
```

正常に実行されると、生成された rawファイルは次の場所に出力されます。

```text
data/raw/
├── raw_tool_catalog.parquet
├── raw_user_directory.parquet
├── raw_access_requests.parquet
├── raw_usage_events_daily.parquet
└── raw_tool_spend_monthly.parquet
```

## 生成された rawファイルの確認

このリポジトリには、DuckDB 向けの確認用 SQL スクリプトも含まれています。

- [`../scripts/inspect_generated_raw_parquet.sql`](../scripts/inspect_generated_raw_parquet.sql)

このスクリプトは、生成された rawデータを直接確認するためのもので、次のような内容を見られます。

- row counts
- schema
- preview rows
- distributions
- time ranges
- duplicate smoke checks
- spend-math smoke checks

使用例:

```bash
duckdb -markdown -f scripts/inspect_generated_raw_parquet.sql > artifacts/validation/inspect_generated_raw_parquet.md
```

このスクリプトは、実用的な確認手段として用意されているものであり、canonical な validation mechanism そのものではありません。

## 関連ドキュメント

- [`../docs/generator_source_contract_and_design_summary.md`](../docs/generator_source_contract_and_design_summary.md)
- [`../artifacts/validation/generator_validation_summary.md`](../artifacts/validation/generator_validation_summary.md)
- [`../scripts/inspect_generated_raw_parquet.sql`](../scripts/inspect_generated_raw_parquet.sql)

## この文書の位置づけ

このリポジトリにおいて、この Generator は warehouse layer のための source-contract provider として読むのが適切です。

このプロジェクトでレビューア向けに主な価値を持つのは、下流の実装です。

- dbt sources
- staging models
- dimensions and facts
- marts
- tests
- dbt docs
- static governance reporting

そのため、この文書は意図的に軽量な内容にとどめています。  
プロジェクト全体の概要については、リポジトリルートの [`README.ja.md`](../README.ja.md) から見てください。

## License

MIT License. See `LICENSE` file.
