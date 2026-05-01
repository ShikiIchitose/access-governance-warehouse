# BigQuery Build Summary

Execution date: 2026-04-30  
dbt version: 1.11.8  
dbt-bigquery version: 1.11.1  
BigQuery project: `<masked-project-id>`  
BigQuery location: `asia-northeast1`  
Raw dataset: `access_governance_raw`  
dbt dataset: `access_governance_dbt`  

## Command

```bash
uv run dbt build --target bigquery_dev
```

## Result Summary

| Item | Value |
|---|---:|
| Models built | 19 |
| Data tests run | 315 |
| Total passed nodes | 334 |
| Warnings | 0 |
| Errors | 0 |
| Skipped | 0 |
| No-op | 0 |

## Result

```text
Completed successfully
Done. PASS=334 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=334
```

## Notes

The BigQuery target successfully built the same dbt model tree used by the local DuckDB path.

The build includes:

- 5 staging views
- 5 core views
- 5 intermediate views
- 4 mart tables
- 315 dbt data tests

The Google Cloud project ID is intentionally masked in committed artifacts.
