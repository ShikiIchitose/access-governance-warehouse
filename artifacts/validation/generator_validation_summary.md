# Generator Validation Summary

## Run Context

- Spec version: `v0.1.0`
- Seed: `18790314`
- Anchor month: `2025-12-01`
- Window months: `12`
- Dry run: `False`
- All checks passed: `True`
- Check count: `13`

## Raw Row Counts

- `raw_tool_catalog`: `5`
- `raw_user_directory`: `198`
- `raw_access_requests`: `553`
- `raw_usage_events_daily`: `30000`
- `raw_tool_spend_monthly`: `313`

## Raw Output Paths

- `raw_tool_catalog`: `access-governance-warehouse/data/raw/raw_tool_catalog.parquet`
- `raw_user_directory`: `access-governance-warehouse/data/raw/raw_user_directory.parquet`
- `raw_access_requests`: `access-governance-warehouse/data/raw/raw_access_requests.parquet`
- `raw_usage_events_daily`: `access-governance-warehouse/data/raw/raw_usage_events_daily.parquet`
- `raw_tool_spend_monthly`: `access-governance-warehouse/data/raw/raw_tool_spend_monthly.parquet`

## Validation Output Paths

- `generator_validation_summary_markdown`: `access-governance-warehouse/artifacts/validation/generator_validation_summary.md`
- `generator_validation_summary_json`: `access-governance-warehouse/artifacts/validation/generator_validation_summary.json`

## Table-local QA

- **PASS** `raw_tool_catalog_local_contract` — Canonical schema, seed-order, and allowed-value checks passed.
- **PASS** `raw_user_directory_local_contract` — Canonical schema, quotas, ordering, and user-universe checks passed.
- **PASS** `raw_access_requests_local_contract` — Canonical schema, workflow nullability, references, and ordering checks passed.
- **PASS** `raw_usage_events_daily_local_contract` — Canonical schema, row-range, pair-state, metric, and ordering checks passed.
- **PASS** `raw_tool_spend_monthly_local_contract` — Canonical schema, spend math, seat constraints, and ordering checks passed.

## Cross-table QA

- **PASS** `access_request_cross_table_relationships` — Access-request requester, reviewer, and tool references resolve against final raw dimension seeds.
- **PASS** `usage_cross_table_relationships` — Usage user and tool references resolve against final raw dimension seeds.
- **PASS** `spend_cross_table_relationships` — Spend tool references and team-to-department mappings are consistent with final raw seeds.
- **PASS** `inactive_user_exclusion` — Inactive users are excluded from final requester, reviewer, and usage records.

## Schema Realization QA (Pre-write)

- **PASS** `raw_table_bundle_contract` — Five canonical raw tables are present in memory with canonical naming.
- **PASS** `output_path_contract` — Canonical raw-output and validation-artifact paths are configured.

## Schema Realization QA (Post-write)

- **PASS** `raw_parquet_files_written` — All canonical raw parquet outputs exist on disk and are non-empty.
- **PASS** `validation_artifacts_written` — All canonical validation artifacts exist on disk and are non-empty.
