# BigQuery Relation Inventory

Execution date: 2026-04-30  
BigQuery project: `<masked-project-id>`  
BigQuery location: `asia-northeast1`  
Raw dataset: `access_governance_raw`  
dbt dataset: `access_governance_dbt`  

## Raw Tables

| Relation | Type | Rows | Notes |
|---|---|---:|---|
| `access_governance_raw.raw_tool_catalog` | table | 5 | Loaded from `data/raw/raw_tool_catalog.parquet` |
| `access_governance_raw.raw_user_directory` | table | 198 | Loaded from `data/raw/raw_user_directory.parquet` |
| `access_governance_raw.raw_access_requests` | table | 553 | Loaded from `data/raw/raw_access_requests.parquet` |
| `access_governance_raw.raw_usage_events_daily` | table | 30000 | Loaded from `data/raw/raw_usage_events_daily.parquet` |
| `access_governance_raw.raw_tool_spend_monthly` | table | 313 | Loaded from `data/raw/raw_tool_spend_monthly.parquet` |

## dbt Relations

### Staging

| Relation | Type | Notes |
|---|---|---|
| `access_governance_dbt.stg_access_governance__tool_catalog` | view | Staging model |
| `access_governance_dbt.stg_access_governance__user_directory` | view | Staging model |
| `access_governance_dbt.stg_access_governance__access_requests` | view | Staging model |
| `access_governance_dbt.stg_access_governance__usage_events_daily` | view | Staging model |
| `access_governance_dbt.stg_access_governance__tool_spend_monthly` | view | Staging model |

### Core

| Relation | Type | Notes |
|---|---|---|
| `access_governance_dbt.dim_tool` | view | Dimension model |
| `access_governance_dbt.dim_user` | view | Dimension model |
| `access_governance_dbt.fct_access_request` | view | Fact model |
| `access_governance_dbt.fct_tool_usage_daily` | view | Fact model |
| `access_governance_dbt.fct_tool_spend_monthly` | view | Fact model |

### Intermediate

| Relation | Type | Notes |
|---|---|---|
| `access_governance_dbt.int_access_requests_open_at_month_end` | view | Intermediate governance model |
| `access_governance_dbt.int_tool_usage_aggregated_to_month_team_tool` | view | Intermediate governance model |
| `access_governance_dbt.int_user_tool_approved_as_of_month_end` | view | Intermediate governance model |
| `access_governance_dbt.int_user_tool_approved_current` | view | Intermediate governance model |
| `access_governance_dbt.int_user_tool_recent_usage_30d` | view | Intermediate governance model |

### Marts

| Relation | Type | Rows | Notes |
|---|---|---:|---|
| `access_governance_dbt.access_requests_monthly` | table | 347 | Mart table |
| `access_governance_dbt.tool_adoption_monthly` | table | 341 | Mart table |
| `access_governance_dbt.governance_exceptions_current` | table | 411 | Mart table |
| `access_governance_dbt.adoption_review_candidates_monthly` | table | 341 | Mart table |

## Notes

This inventory documents the BigQuery execution path after a successful dbt build.

The committed artifact intentionally masks the Google Cloud project ID while keeping dataset and relation names visible for review.

The local DuckDB path remains the primary clone-and-run review path. The BigQuery path is documented as cloud execution evidence.
