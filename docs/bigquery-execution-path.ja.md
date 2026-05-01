# BigQuery 実行パス（BigQuery Execution Path）

この文書は、`access-governance-warehouse` project における BigQuery execution path を再現する手順を説明します。

ローカル DuckDB path は、clone してすぐ確認できる primary review path として維持しています。  
BigQuery path は、同じ dbt source contract、models、tests を Google BigQuery 上でも検証したい reviewer 向けの任意の cloud execution path です。

## 1. 構成（Architecture）

### ローカル path（Local path）

```text
data/raw/*.parquet
  -> DuckDB
  -> dbt
  -> marts
  -> static governance report
```

### BigQuery path

```text
data/raw/*.parquet
  -> BigQuery raw tables
  -> dbt BigQuery target
  -> BigQuery dbt dataset
  -> marts
```

BigQuery path は、DuckDB path と同じ dbt model tree を使用します。source contract は次のファイルで共有されています。

```text
models/sources/sources.yml
```

DuckDB target では、sources はローカル Parquet files から読み込まれます。  
BigQuery target では、同じ logical sources が BigQuery raw tables として読み込まれていることを前提とします。

## 2. 必要な Google Cloud resources

推奨値は次の通りです。

| Resource | Value |
|---|---|
| BigQuery location | `asia-northeast1` |
| Raw dataset | `access_governance_raw` |
| dbt output dataset | `access_governance_dbt` |

公開ドキュメントでは、project ID として次の placeholder を使用します。

```text
your-gcp-project-id
```

## 3. 前提条件（Prerequisites）

Google Cloud CLI をインストールし、`gcloud` と `bq` の両方が利用できることを確認します。

```bash
gcloud --version
bq version
```

メイン README の手順に従って repository を clone し、project dependencies をインストールします。以降のコマンドは repository root から実行します。

```bash
uv sync
```

ローカル shell variables を設定します。

```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export BQ_LOCATION="asia-northeast1"
```

変数に suffix を付ける場合は、`${...}` を使用します。

```bash
echo "${GCP_PROJECT_ID}:access_governance_raw"
echo "${GCP_PROJECT_ID}:access_governance_dbt"
```

## 4. ローカル認証（Authenticate locally）

Google Cloud CLI にログインします。

```bash
gcloud auth login
```

ローカル開発ツール向けに Application Default Credentials を作成します。

```bash
gcloud auth application-default login
```

Application Default Credentials の quota project を設定します。

```bash
gcloud auth application-default set-quota-project "${GCP_PROJECT_ID}"
```

active Google Cloud project を設定します。

```bash
gcloud config set project "${GCP_PROJECT_ID}"
gcloud config get-value project
```

## 5. BigQuery API を有効化する

BigQuery API が有効になっているか確認します。

```bash
gcloud services list \
  --enabled \
  --project "${GCP_PROJECT_ID}" \
  --filter="config.name:bigquery.googleapis.com"
```

必要であれば有効化します。

```bash
gcloud services enable bigquery.googleapis.com \
  --project "${GCP_PROJECT_ID}"
```

## 6. BigQuery datasets を作成する

raw dataset を作成します。

```bash
bq --location="${BQ_LOCATION}" mk \
  --dataset \
  --description "Raw synthetic access governance tables loaded from local Parquet fixtures." \
  "${GCP_PROJECT_ID}:access_governance_raw"
```

dbt output dataset を作成します。

```bash
bq --location="${BQ_LOCATION}" mk \
  --dataset \
  --description "dbt-built access governance warehouse models and marts." \
  "${GCP_PROJECT_ID}:access_governance_dbt"
```

datasets を確認します。

```bash
bq ls --project_id "${GCP_PROJECT_ID}"
```

dataset metadata を確認します。

```bash
bq show --format=prettyjson "${GCP_PROJECT_ID}:access_governance_raw"
bq show --format=prettyjson "${GCP_PROJECT_ID}:access_governance_dbt"
```

両方の datasets が次の location を使用していることを確認します。

```text
location: asia-northeast1
```

## 7. raw Parquet files を BigQuery に読み込む

BigQuery raw dataset には、次の directory 配下にコミットされている Parquet fixtures から読み込んだ 5 つの raw tables が含まれる想定です。

```text
data/raw/
```

想定される raw files は次の通りです。

```text
data/raw/raw_tool_catalog.parquet
data/raw/raw_user_directory.parquet
data/raw/raw_access_requests.parquet
data/raw/raw_usage_events_daily.parquet
data/raw/raw_tool_spend_monthly.parquet
```

### Option A: helper script で読み込む

この repository には、5 つの raw Parquet files を BigQuery に一括で読み込む helper script が含まれています。

デフォルトでは、この helper は `WRITE_TRUNCATE` を使用します。  
そのため、再実行すると duplicate rows を append するのではなく、raw tables を置き換えます。

load plan を dry-run します。

```bash
uv run python scripts/load_raw_to_bigquery.py \
  --project-id "${GCP_PROJECT_ID}" \
  --location "${BQ_LOCATION}" \
  --dry-run
```

問題なければ load を実行します。

```bash
uv run python scripts/load_raw_to_bigquery.py \
  --project-id "${GCP_PROJECT_ID}" \
  --location "${BQ_LOCATION}"
```

想定される読み込み後の row counts は次の通りです。

| Raw table | Rows |
|---|---:|
| `raw_tool_catalog` | 5 |
| `raw_user_directory` | 198 |
| `raw_access_requests` | 553 |
| `raw_usage_events_daily` | 30000 |
| `raw_tool_spend_monthly` | 313 |

### Option B: bq CLI で手動読み込みする

手動の `bq load` commands は、transparent reference path として残しています。

```bash
bq --location="${BQ_LOCATION}" load \
  --source_format=PARQUET \
  --replace \
  "${GCP_PROJECT_ID}:access_governance_raw.raw_tool_catalog" \
  data/raw/raw_tool_catalog.parquet
```

```bash
bq --location="${BQ_LOCATION}" load \
  --source_format=PARQUET \
  --replace \
  "${GCP_PROJECT_ID}:access_governance_raw.raw_user_directory" \
  data/raw/raw_user_directory.parquet
```

```bash
bq --location="${BQ_LOCATION}" load \
  --source_format=PARQUET \
  --replace \
  "${GCP_PROJECT_ID}:access_governance_raw.raw_access_requests" \
  data/raw/raw_access_requests.parquet
```

```bash
bq --location="${BQ_LOCATION}" load \
  --source_format=PARQUET \
  --replace \
  "${GCP_PROJECT_ID}:access_governance_raw.raw_usage_events_daily" \
  data/raw/raw_usage_events_daily.parquet
```

```bash
bq --location="${BQ_LOCATION}" load \
  --source_format=PARQUET \
  --replace \
  "${GCP_PROJECT_ID}:access_governance_raw.raw_tool_spend_monthly" \
  data/raw/raw_tool_spend_monthly.parquet
```

raw tables を確認します。

```bash
bq ls "${GCP_PROJECT_ID}:access_governance_raw"
```

row counts を確認します。

```bash
bq query \
  --location="${BQ_LOCATION}" \
  --use_legacy_sql=false \
  "
  with row_counts as (
    select
      1 as sort_order,
      'raw_tool_catalog' as table_name,
      count(*) as row_count
    from \`${GCP_PROJECT_ID}.access_governance_raw.raw_tool_catalog\`

    union all

    select
      2 as sort_order,
      'raw_user_directory' as table_name,
      count(*) as row_count
    from \`${GCP_PROJECT_ID}.access_governance_raw.raw_user_directory\`

    union all

    select
      3 as sort_order,
      'raw_access_requests' as table_name,
      count(*) as row_count
    from \`${GCP_PROJECT_ID}.access_governance_raw.raw_access_requests\`

    union all

    select
      4 as sort_order,
      'raw_usage_events_daily' as table_name,
      count(*) as row_count
    from \`${GCP_PROJECT_ID}.access_governance_raw.raw_usage_events_daily\`

    union all

    select
      5 as sort_order,
      'raw_tool_spend_monthly' as table_name,
      count(*) as row_count
    from \`${GCP_PROJECT_ID}.access_governance_raw.raw_tool_spend_monthly\`
  )

  select
    table_name,
    row_count
  from row_counts
  order by
    sort_order
  "
```

## 8. dbt BigQuery target を設定する

この repository には example profile が含まれています。

```text
profiles/profiles.bigquery.yml.example
```

該当する `bigquery_dev` output を、ローカルの dbt profile にコピーします。

ローカル profile path は次の通りです。

```text
~/.dbt/profiles.yml
```

example shape は次の通りです。

```yaml
access_governance_warehouse:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: data/warehouse/access_governance.duckdb
      threads: 5

    bigquery_dev:
      type: bigquery
      method: oauth
      project: your-gcp-project-id
      dataset: access_governance_dbt
      location: asia-northeast1
      threads: 5
      job_execution_timeout_seconds: 300
      job_retries: 1
```

この example は、次のコマンドで作成した local OAuth-based Application Default Credentials を使用します。

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "${GCP_PROJECT_ID}"
```

BigQuery target を実行する前に、project ID environment variable を設定します。

```bash
export GCP_PROJECT_ID="your-gcp-project-id"
```

共有 source configuration は、この environment variable を使用して raw sources の BigQuery project を解決します。

## 9. dbt connection と build を検証する

BigQuery target を検証します。

```bash
uv run dbt debug --target bigquery_dev
```

BigQuery target に対して project を parse します。

```bash
uv run dbt parse --target bigquery_dev
```

BigQuery に対して models を build し、tests を実行します。

```bash
uv run dbt build --target bigquery_dev
```

data tests のみを実行します。

```bash
uv run dbt test --target bigquery_dev
```

検証済みの v0.2.0 BigQuery baseline は次の通りです。

```text
dbt build --target bigquery_dev:
  PASS=334 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=334

dbt test --target bigquery_dev:
  PASS=315 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=315
```

BigQuery target は、ローカル DuckDB path で使用しているものと同じ logical source contract、staging layer、core layer、intermediate layer、marts を検証します。  
BigQuery 専用の model tree は維持していません。

## 10. BigQuery 実行証跡（BigQuery execution evidence）

コミット済みの evidence artifacts は次の通りです。

| Artifact | 目的 |
|---|---|
| [`artifacts/cloud/bigquery_build_summary.md`](../artifacts/cloud/bigquery_build_summary.md) | BigQuery dbt build result |
| [`artifacts/cloud/bigquery_test_summary.md`](../artifacts/cloud/bigquery_test_summary.md) | BigQuery dbt data test result |
| [`artifacts/cloud/bigquery_relation_inventory.md`](../artifacts/cloud/bigquery_relation_inventory.md) | BigQuery raw and dbt relation inventory |

これらの artifacts では、dataset names と relation names を見える状態に保ちつつ、Google Cloud project ID を意図的に mask しています。

## 11. ローカル path は変更しない

ローカル DuckDB path は、primary reproducible review path として維持します。

```bash
uv run dbt build
uv run python scripts/build_governance_report.py
```

## 12. コストに関する注意（Cost notes）

この project は、小さな決定論的 synthetic dataset を使用します。  
BigQuery usage は小さいままになる想定ですが、BigQuery では storage costs と query costs が発生する可能性があります。

推奨する safeguards は次の通りです。

```text
- この portfolio work 専用の Google Cloud project を使用する。
- datasets は asia-northeast1 に置く。
- 関係のない大規模 public datasets を query しない。
- 大きな query を実行する前に bytes processed を確認する。
- 不要になった datasets は削除する。
```

## 13. 不要になった datasets を削除する

必要であれば、dbt output dataset を削除します。

```bash
bq rm -r -f -d "${GCP_PROJECT_ID}:access_governance_dbt"
```

必要であれば、raw dataset を削除します。

```bash
bq rm -r -f -d "${GCP_PROJECT_ID}:access_governance_raw"
```

削除されたことを確認します。

```bash
bq ls --project_id "${GCP_PROJECT_ID}"
```

## 14. 公開 artifact の masking policy

公開 screenshots とコミット済み artifacts では、次の情報を mask しています。

```text
- Google Cloud project ID
- user email addresses
- service account emails
- etag values
- billing-related identifiers
- private account-specific identifiers
```

見えていてよい names は次の通りです。

```text
- access_governance_raw
- access_governance_dbt
- raw_access_requests
- tool_adoption_monthly
- governance_exceptions_current
```
