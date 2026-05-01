# BigQuery Test Summary

Execution date: 2026-04-30  
BigQuery project: `<masked-project-id>`  
BigQuery location: `asia-northeast1`  

## Command

```bash
uv run dbt test --target bigquery_dev
```

## Result Summary

| Item | Value |
|---|---:|
| Total data tests | 315 |
| Passed | 315 |
| Warnings | 0 |
| Errors | 0 |
| Skipped | 0 |
| No-op | 0 |

## Result

```text
Completed successfully
Done. PASS=315 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=315
```

## Notes

The existing dbt data quality design was validated against the BigQuery target.

The BigQuery target validates the same logical source contract, staging layer, core layer, intermediate layer, and marts used by the local DuckDB path, without maintaining a separate BigQuery-specific model tree.
