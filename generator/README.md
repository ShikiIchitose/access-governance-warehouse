# Synthetic Raw Generator

> 日本語版: [README.ja.md](README.ja.md)

This directory contains the synthetic raw data generator for `access-governance-warehouse`.

The generator is a supporting component of the repository, not the main portfolio artifact.  
Its role is to produce a deterministic, inspectable raw dataset that the downstream DuckDB + dbt warehouse models can build from.

## Why this exists

The main project is a dbt-centered local warehouse portfolio.  
This generator exists to provide a stable local source contract for that warehouse work.

Instead of using arbitrary random tables, the generator produces rule-based synthetic business data for an access-governance domain:

1. entity setup
2. request volume
3. request context
4. review outcome
5. usage
6. spend

This causal ordering is intentional so that downstream marts can answer realistic business questions about requests, approvals, adoption, exceptions, and spend.

## What it produces

The generator emits five raw Parquet files under `data/raw/`:

- `raw_tool_catalog.parquet`
- `raw_user_directory.parquet`
- `raw_access_requests.parquet`
- `raw_usage_events_daily.parquet`
- `raw_tool_spend_monthly.parquet`

These raw files are the actual deliverables of the generator.

The local DuckDB file at `data/warehouse/access_governance.duckdb` is a downstream warehouse artifact for SQL and dbt work. It is not the generator's primary output.

## Design characteristics

The generator is designed to be:

- deterministic
- inspectable
- reproducible
- business-rule-driven
- locally runnable

For v0.1.0, the dataset is generated with:

- fixed seed: `18790314`
- fixed anchor month: `2025-12-01`
- reporting window: 12 months

The implementation uses:

- `pandas` for tabular assembly and final raw-table construction
- pure Python stateful logic for deterministic workflow steps such as slot realization, request assignment, duplicate-policy reconciliation, and review routing

## Output contract

The raw layer preserves explicit table grains:

- `raw_tool_catalog`: one row per tool
- `raw_user_directory`: one row per user
- `raw_access_requests`: one row per access request
- `raw_usage_events_daily`: one row per user × tool × day
- `raw_tool_spend_monthly`: one row per month × team × tool

Configured row-count targets for the default v0.1.0 setup are shown below. Some downstream validation rules may use documented acceptance ranges where applicable.

- `raw_tool_catalog`: 5
- `raw_user_directory`: 198
- `raw_access_requests`: 553
- `raw_usage_events_daily`: 30000
- `raw_tool_spend_monthly`: 313

The generator also enforces core raw-contract rules such as:

- canonical column order
- deterministic row order
- resolvable cross-table references
- raw-grain uniqueness
- status-aware nullability
- inactive-user exclusion from requester / reviewer / usage selection where applicable

## Validation

Generator outputs are validated before and after write.

The generator validates outputs through:

- table-local QA
- cross-table QA
- schema-realization QA
- raw output existence checks
- validation artifact existence checks

Validation artifacts:

- [`../artifacts/validation/generator_validation_summary.md`](../artifacts/validation/generator_validation_summary.md)
- [`../artifacts/validation/generator_validation_summary.json`](../artifacts/validation/generator_validation_summary.json)

These files are the canonical validation artifacts for generator output quality.

## Quick run

Run from the repository root:

```bash
uv sync
uv run python -m scripts.generate_synthetic_raw
```

After a successful run, the generated raw files should appear under:

```text
data/raw/
├── raw_tool_catalog.parquet
├── raw_user_directory.parquet
├── raw_access_requests.parquet
├── raw_usage_events_daily.parquet
└── raw_tool_spend_monthly.parquet
```

## Inspecting the generated raw files

This repository also includes a DuckDB-oriented inspection script:

- [`../scripts/inspect_generated_raw_parquet.sql`](../scripts/inspect_generated_raw_parquet.sql)

Its purpose is to inspect generated raw outputs directly, including:

- row counts
- schema
- preview rows
- distributions
- time ranges
- duplicate smoke checks
- spend-math smoke checks

Example usage:

```bash
duckdb -markdown -f scripts/inspect_generated_raw_parquet.sql > artifacts/validation/inspect_generated_raw_parquet.md
```

This script is intended as a practical inspection aid, not as the canonical validation mechanism.

## Related documents

- [`../docs/generator_source_contract_and_design_summary.md`](../docs/generator_source_contract_and_design_summary.md)
- [`../artifacts/validation/generator_validation_summary.md`](../artifacts/validation/generator_validation_summary.md)
- [`../scripts/inspect_generated_raw_parquet.sql`](../scripts/inspect_generated_raw_parquet.sql)

## Scope note

For this repository, the generator should be read as a source-contract provider for the warehouse layer.

The main reviewer-facing value of the project is in the downstream work:

- dbt sources
- staging models
- dimensions and facts
- marts
- tests
- dbt docs
- static governance reporting

Accordingly, this document is intentionally lightweight.
For the full project overview, start from the repository root [`README.md`](../README.md).

## License

MIT License. See `LICENSE` file.
