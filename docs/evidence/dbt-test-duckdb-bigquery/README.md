# DuckDB and BigQuery dbt Test Execution Record

[日本語版](./README.ja.md)

## Overview

This directory contains recorded results from running the same set of dbt data
tests against DuckDB and BigQuery.

The purpose of this record is to document an observation made during the
development of the
[`access-governance-warehouse`](../../../README.md) portfolio project.

This record is not intended to serve as a general performance benchmark of
DuckDB or BigQuery.

## Background

The project supports two execution targets:

- DuckDB for local development and validation
- BigQuery for execution on a cloud data warehouse

During development, a noticeable difference was observed in the time required
to execute many small dbt data tests against the two targets.

To preserve this observation, the same set of 315 data tests was executed with
five threads in each environment.

## Commands

### BigQuery

```bash
uv run dbt test --target bigquery_dev
```

### DuckDB

```bash
uv run dbt test
```

## Execution conditions

| Item | BigQuery | DuckDB |
|---|---|---|
| dbt Core | 1.11.8 | 1.11.8 |
| Adapter | dbt-bigquery 1.11.1 | dbt-duckdb 1.10.1 |
| Data tests | 315 | 315 |
| Threads | 5 | 5 |
| Passed | 315 | 315 |
| Warnings | 0 | 0 |
| Errors | 0 | 0 |
| Skipped | 0 | 0 |

The tests were executed against the small synthetic dataset used by this
portfolio project.

## Recorded results

| Target | Duration |
|---|---:|
| DuckDB | 6.97 seconds |
| BigQuery | 58.80 seconds |

In this pair of recorded executions, the BigQuery target required approximately
8.4 times the duration of the DuckDB target.

The difference in total execution time was 51.83 seconds.

## Observed execution pattern

The logs show that many individual tests completed in approximately the
following ranges:

| Target | Approximate duration of many individual tests |
|---|---:|
| DuckDB | 0.07–0.12 seconds |
| BigQuery | 0.6–1.3 seconds |

Some tests fell outside these approximate ranges.

The recorded pattern indicates that, for this specific workload, the time
associated with executing many small test queries accumulated into a
substantial difference in total duration.

The logs do not identify how much of the difference was caused by any
individual factor.

Possible contributing factors include:

- remote query submission
- network communication
- authentication and API communication
- query scheduling
- distributed query execution
- storage access
- adapter-specific behavior
- caching state

These are hypotheses. They were not isolated or measured in this execution
record.

## Interpretation

This record supports the following limited statement:

> In one recorded execution of this portfolio project, running 315 dbt data
> tests with five threads took 58.80 seconds on BigQuery and 6.97 seconds on
> DuckDB.

It does not support the following general conclusions:

- BigQuery is generally slower than DuckDB.
- BigQuery is approximately 8.4 times slower for other workloads.
- The difference was caused solely by fixed query overhead.
- DuckDB is a better execution engine for production analytics workloads.
- The result will remain the same as data volume or query complexity increases.

DuckDB and BigQuery have different architectures and intended operating
contexts.

DuckDB executes queries locally within the application process. BigQuery is a
distributed cloud data warehouse that receives and executes queries through a
remote service.

A result obtained from a small synthetic dataset and many small test queries
should not be generalized to large data scans, complex transformations,
concurrent workloads, or production operations.

## Limitations

This record has the following limitations:

- Only one recorded execution per target is included.
- The runs were not repeated to calculate a median or variance.
- Warm-cache and cold-cache conditions were not separated.
- Network latency was not measured independently.
- Authentication and API latency were not measured independently.
- Query scheduling time was not isolated.
- Adapter versions were not identical.
- The execution engines and storage locations were different.
- The dataset was synthetic and small.
- Query-processing cost was not analyzed.
- The tests were not grouped by query complexity.

For these reasons, this record should be treated as an implementation
observation rather than a controlled benchmark.

## Why this record is included

The observation raised a broader design question:

> How do data volume, query characteristics, execution environment, freshness
> requirements, operational capacity, and other constraints affect an
> appropriate data pipeline architecture?

The execution-time difference is therefore used as a starting point for
further investigation, not as a product comparison or architecture
recommendation.

## Evidence files

The following files contain sanitized excerpts from the recorded command
outputs:

- [`bigquery-test-summary.txt`](./bigquery-test-summary.txt)
- [`duckdb-test-summary.txt`](./duckdb-test-summary.txt)

The excerpts retain the information required to confirm:

- the dbt Core version
- the adapter and adapter version
- the number of detected data tests
- the configured thread count
- the total execution duration
- the final pass, warning, error, and skip counts

Verbose output for each of the 315 individual tests is omitted from the
published excerpts because it does not materially change the documented
observation.
