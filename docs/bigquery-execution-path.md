# BigQuery Execution Path

This document describes how to reproduce the BigQuery execution path for the
`access-governance-warehouse` project.

The local DuckDB path remains the primary clone-and-run review path. The
BigQuery path is an optional cloud execution path for reviewers who want to
validate the same dbt source contract, models, and tests on Google BigQuery.

## 1. Architecture

### Local path

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

The BigQuery path uses the same dbt model tree as the DuckDB path. The source
contract is shared in:

```text
models/sources/sources.yml
```

For the DuckDB target, sources are read from local Parquet files. For the
BigQuery target, the same logical sources are expected to exist as loaded
BigQuery raw tables.

## 2. Required Google Cloud resources

Recommended values:

| Resource | Value |
|---|---|
| BigQuery location | `asia-northeast1` |
| Raw dataset | `access_governance_raw` |
| dbt output dataset | `access_governance_dbt` |

The public documentation uses a placeholder project ID:

```text
your-gcp-project-id
```

Do not commit real credential files, service account keys, billing information,
or private account-specific identifiers.

## 3. Prerequisites

Install the Google Cloud CLI and confirm that both `gcloud` and `bq` are
available.

```bash
gcloud --version
bq version
```

Clone the repository as shown in the main README, install project dependencies, and run commands from the repository root.

```bash
uv sync
```

Set local shell variables.

```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export BQ_LOCATION="asia-northeast1"
```

Use `${...}` when appending suffixes to variables.

```bash
echo "${GCP_PROJECT_ID}:access_governance_raw"
echo "${GCP_PROJECT_ID}:access_governance_dbt"
```

## 4. Authenticate locally

Authenticate the Google Cloud CLI.

```bash
gcloud auth login
```

Create Application Default Credentials for local development tools.

```bash
gcloud auth application-default login
```

Set the quota project for Application Default Credentials.

```bash
gcloud auth application-default set-quota-project "${GCP_PROJECT_ID}"
```

Set the active Google Cloud project.

```bash
gcloud config set project "${GCP_PROJECT_ID}"
gcloud config get-value project
```

## 5. Enable the BigQuery API

Check whether the BigQuery API is enabled.

```bash
gcloud services list \
  --enabled \
  --project "${GCP_PROJECT_ID}" \
  --filter="config.name:bigquery.googleapis.com"
```

Enable it if needed.

```bash
gcloud services enable bigquery.googleapis.com \
  --project "${GCP_PROJECT_ID}"
```

## 6. Create BigQuery datasets

Create the raw dataset.

```bash
bq --location="${BQ_LOCATION}" mk \
  --dataset \
  --description "Raw synthetic access governance tables loaded from local Parquet fixtures." \
  "${GCP_PROJECT_ID}:access_governance_raw"
```

Create the dbt output dataset.

```bash
bq --location="${BQ_LOCATION}" mk \
  --dataset \
  --description "dbt-built access governance warehouse models and marts." \
  "${GCP_PROJECT_ID}:access_governance_dbt"
```

Confirm the datasets.

```bash
bq ls --project_id "${GCP_PROJECT_ID}"
```

Inspect dataset metadata.

```bash
bq show --format=prettyjson "${GCP_PROJECT_ID}:access_governance_raw"
bq show --format=prettyjson "${GCP_PROJECT_ID}:access_governance_dbt"
```

Both datasets should use:

```text
location: asia-northeast1
```

## 7. Load raw Parquet files into BigQuery

The BigQuery raw dataset should contain five raw tables loaded from the committed Parquet fixtures under:

```text
data/raw/
```

Expected raw files:

```text
data/raw/raw_tool_catalog.parquet
data/raw/raw_user_directory.parquet
data/raw/raw_access_requests.parquet
data/raw/raw_usage_events_daily.parquet
data/raw/raw_tool_spend_monthly.parquet
```

### Option A: load with the helper script

The repository includes a helper script that loads all five raw Parquet files into BigQuery with overwrite semantics.

By default, the helper uses `WRITE_TRUNCATE`, so rerunning it replaces the raw tables instead of appending duplicate rows.

Dry-run the load plan:

```bash
uv run python scripts/load_raw_to_bigquery.py \
  --project-id "${GCP_PROJECT_ID}" \
  --location "${BQ_LOCATION}" \
  --dry-run
```

Run the load:

```bash
uv run python scripts/load_raw_to_bigquery.py \
  --project-id "${GCP_PROJECT_ID}" \
  --location "${BQ_LOCATION}"
```

Expected loaded row counts:

| Raw table | Rows |
|---|---:|
| `raw_tool_catalog` | 5 |
| `raw_user_directory` | 198 |
| `raw_access_requests` | 553 |
| `raw_usage_events_daily` | 30000 |
| `raw_tool_spend_monthly` | 313 |

### Option B: load manually with the bq CLI

Manual `bq load` commands are kept as the transparent reference path.

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

Confirm the raw tables.

```bash
bq ls "${GCP_PROJECT_ID}:access_governance_raw"
```

Check row counts.

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

## 8. Configure dbt BigQuery target

The repository includes an example profile:

```text
profiles/profiles.bigquery.yml.example
```

Copy the relevant `bigquery_dev` output into your local dbt profile.

Local profile path:

```text
~/.dbt/profiles.yml
```

Example shape:

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

This example uses local OAuth-based Application Default Credentials created by:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "${GCP_PROJECT_ID}"
```

A service account profile can also be used, but service account key files must not be committed to this repository.

Set the project ID environment variable before running the BigQuery target.

```bash
export GCP_PROJECT_ID="your-gcp-project-id"
```

The shared source configuration uses this environment variable to resolve the
BigQuery project for raw sources.

## 9. Validate dbt connection and build

Validate the BigQuery target.

```bash
uv run dbt debug --target bigquery_dev
```

Parse the project against the BigQuery target.

```bash
uv run dbt parse --target bigquery_dev
```

Build models and run tests against BigQuery.

```bash
uv run dbt build --target bigquery_dev
```

Run data tests only.

```bash
uv run dbt test --target bigquery_dev
```

Verified v0.2.0 BigQuery baseline:

```text
dbt build --target bigquery_dev:
  PASS=334 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=334

dbt test --target bigquery_dev:
  PASS=315 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=315
```

The BigQuery target validates the same logical source contract, staging layer, core layer, intermediate layer, and marts used by the local DuckDB path, without maintaining a separate BigQuery-specific model tree.

## 10. BigQuery execution evidence

Committed evidence artifacts:

| Artifact | Purpose |
|---|---|
| [`artifacts/cloud/bigquery_build_summary.md`](../artifacts/cloud/bigquery_build_summary.md) | BigQuery dbt build result |
| [`artifacts/cloud/bigquery_test_summary.md`](../artifacts/cloud/bigquery_test_summary.md) | BigQuery dbt data test result |
| [`artifacts/cloud/bigquery_relation_inventory.md`](../artifacts/cloud/bigquery_relation_inventory.md) | BigQuery raw and dbt relation inventory |

These artifacts intentionally mask the Google Cloud project ID while keeping dataset and relation names visible.

## 11. Local path should remain unchanged

The local DuckDB path remains the primary reproducible review path.

```bash
uv run dbt build
uv run python scripts/build_governance_report.py
```

## 12. Cost notes

This project uses a small deterministic synthetic dataset. BigQuery usage should
remain small, but BigQuery can incur storage and query costs.

Recommended safeguards:

```text
- Use a dedicated Google Cloud project for this portfolio work.
- Keep datasets in asia-northeast1.
- Avoid querying unrelated large public datasets.
- Review bytes processed before running large queries.
- Delete the datasets when they are no longer needed.
```

## 13. Cleanup

Delete the dbt output dataset if needed.

```bash
bq rm -r -f -d "${GCP_PROJECT_ID}:access_governance_dbt"
```

Delete the raw dataset if needed.

```bash
bq rm -r -f -d "${GCP_PROJECT_ID}:access_governance_raw"
```

Confirm removal.

```bash
bq ls --project_id "${GCP_PROJECT_ID}"
```

## 14. Public artifact masking policy

Public screenshots and committed artifacts should mask:

```text
- Google Cloud project ID
- user email addresses
- service account emails
- etag values
- billing-related identifiers
- private account-specific identifiers
```

Visible names:

```text
- access_governance_raw
- access_governance_dbt
- raw_access_requests
- tool_adoption_monthly
- governance_exceptions_current
```
