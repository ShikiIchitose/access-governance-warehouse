# access-governance-warehouse

[![CI](https://github.com/ShikiIchitose/access-governance-warehouse/actions/workflows/ci.yml/badge.svg)](https://github.com/ShikiIchitose/access-governance-warehouse/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ShikiIchitose/access-governance-warehouse?sort=semver&display_name=tag)](https://github.com/ShikiIchitose/access-governance-warehouse/releases/latest)
[![License](https://img.shields.io/github/license/ShikiIchitose/access-governance-warehouse)](LICENSE)

> 日本語版: [README.ja.md](README.ja.md)

A DuckDB + BigQuery + Looker Studio dbt analytics engineering portfolio project for enterprise artificial intelligence access governance.

This repository demonstrates how deterministic synthetic source data can be modeled into a small but credible analytical warehouse using explicit dbt layers, data tests, documentation, a static governance report, an optional BigQuery execution path, and lightweight Looker Studio dashboard artifacts.

The local DuckDB path remains the primary clone-and-run review path. The BigQuery path demonstrates that the same dbt source contract, model tree, and data test suite can also run on a cloud data warehouse. The Looker Studio dashboard artifacts demonstrate that the BigQuery marts can support a stakeholder-facing BI presentation layer.

---

---

## BI-facing dashboard snapshot

v0.2.1 adds lightweight Looker Studio dashboard artifacts connected to BigQuery marts.

The screenshot below shows the Executive Overview page, which summarizes access requests, approval rate, usage volume, spend, and current governance review signals.

This screenshot shows that the mart layer is not limited to SQL models and static reports, but is also extended into a BI-facing artifact that can present decision-making context to executives, business teams, and non-engineering stakeholders.

[View the dashboard documentation](docs/looker-studio-dashboard.md)

![Looker Studio Executive Overview dashboard](docs/assets/looker-studio/executive_overview_dashboard.png)

---

## Overview

`access-governance-warehouse` models an analytical layer for enterprise artificial intelligence tool access governance.

It starts from deterministic synthetic raw Parquet files, loads them through a local DuckDB-backed dbt project, and produces business-facing marts that answer governance, adoption, usage, and spend questions.

The project is designed to demonstrate:

- deterministic synthetic raw data generation
- raw source contracts
- layered dbt modeling
- reusable dimensions and facts
- intermediate stock and flow logic
- business-facing marts
- data quality tests
- dbt documentation and lineage
- a generated static governance report
- optional BigQuery execution validation
- lightweight Looker Studio dashboard artifacts

This repository is conceptually paired with the related Django application repository, but this warehouse uses deterministic file-based synthetic data rather than live application extraction.

---

## Quick review path

For a fast portfolio review, start with the generated report and dashboard artifacts, then inspect the supporting design documents.

| Step | What to open | Why |
|---:|---|---|
| 1 | [`artifacts/reports/governance_report_v0_2_x.md`](artifacts/reports/governance_report_v0_2_x.md) | See the business-facing static output generated from the mart layer |
| 2 | [`docs/looker-studio-dashboard.md`](docs/looker-studio-dashboard.md) | Review the BI-facing Looker Studio dashboard documentation |
| 3 | [`docs/assets/looker-studio/executive_overview_dashboard.png`](docs/assets/looker-studio/executive_overview_dashboard.png) | See the executive dashboard page built from BigQuery marts |
| 4 | [`docs/assets/looker-studio/tool_adoption_dashboard.png`](docs/assets/looker-studio/tool_adoption_dashboard.png) | See the adoption, usage, spend, and cost alignment dashboard page |
| 5 | [`docs/assets/looker-studio/governance_exceptions_dashboard.png`](docs/assets/looker-studio/governance_exceptions_dashboard.png) | See the governance exceptions and review signals dashboard page |
| 6 | [`artifacts/cloud/bigquery_build_summary.md`](artifacts/cloud/bigquery_build_summary.md) | Confirm that the same dbt project was built on BigQuery |
| 7 | [`artifacts/cloud/bigquery_test_summary.md`](artifacts/cloud/bigquery_test_summary.md) | Confirm that all dbt data tests passed on BigQuery |
| 8 | [`artifacts/cloud/bigquery_relation_inventory.md`](artifacts/cloud/bigquery_relation_inventory.md) | Inspect the BigQuery raw and dbt relation inventory |
| 9 | [`docs/domain-modeling-and-assumptions.md`](docs/domain-modeling-and-assumptions.md) | Understand model grain, assumptions, and scope boundaries |
| 10 | [`docs/testing-strategy.md`](docs/testing-strategy.md) | Understand the dbt testing strategy and validation philosophy |
| 11 | [`docs/bigquery-execution-path.md`](docs/bigquery-execution-path.md) | Reproduce or inspect the optional BigQuery execution path |
| 12 | `models/marts/governance/` | Inspect the business-facing mart SQL |

---

## Highlights

- End-to-end local analytics engineering workflow using DuckDB and dbt.
- Cloud warehouse execution validation using BigQuery and the same dbt project.
- Lightweight Looker Studio dashboard artifacts connected to BigQuery marts.
- Deterministic synthetic raw data with explicit source contracts.
- Layered dbt models from sources to staging, core, intermediate, and marts.
- 315 dbt data tests covering source contracts, grains, reconciliation, and mart logic.
- Static governance report generated from business-facing marts.
- Clear separation between data transformation failures and business review signals.
- Optional BigQuery execution path using the same dbt model tree as the local DuckDB path.
- BigQuery raw loading helper for committed Parquet fixtures.
- BigQuery execution evidence with build, test, and relation inventory artifacts.
- Screenshot-based BI artifacts that do not require a public Looker Studio report link.

---

## Business questions

The warehouse and dashboard artifacts are designed to answer five focused questions:

1. Which teams request, approve, or reject which tools over time?
2. Are approved tools actually used?
3. Which user-tool relationships show usage without approved access?
4. Is spend directionally aligned with adoption and usage?
5. Can the mart layer support stakeholder-facing BI reporting without moving business logic out of dbt?

---

## Architecture

```text
Synthetic raw generator
        |
        v
data/raw/*.parquet
        |
        +-----------------------------+
        |                             |
        v                             v
DuckDB local warehouse        BigQuery raw tables
        |                             |
        v                             v
dbt DuckDB target             dbt BigQuery target
        |                             |
        +-------------+---------------+
                      |
                      v
same dbt model tree
sources -> staging -> core -> intermediate -> marts
                      |
          +-----------+-----------+
          |                       |
          v                       v
static governance report    Looker Studio dashboard artifacts
                            from BigQuery marts
```

---

## Local, cloud, and BI-facing paths

The local DuckDB path is the primary reproducible review path. It requires no cloud account and can be run from a fresh clone.

The BigQuery path is an optional cloud execution path. It validates that the same logical source contract, staging layer, core layer, intermediate layer, marts, and dbt data tests can run on Google BigQuery without maintaining a separate BigQuery-specific model tree.

The Looker Studio path is a BI-facing artifact layer on top of the BigQuery marts. It is documented through screenshots and dashboard documentation rather than a required public report link.

| Path | Purpose | Reproducibility |
|---|---|---|
| DuckDB local path | Clone-and-run local warehouse review | Fully reproducible from this repository |
| BigQuery path | Cloud data warehouse execution validation | Reproducible with a reviewer-owned Google Cloud project |
| Static governance report | Reviewer-facing analytical output | Generated locally from DuckDB marts |
| Looker Studio dashboard artifacts | BI-facing presentation evidence from BigQuery marts | Reviewable through committed screenshots and documentation |

---

## dbt lineage

The dbt lineage graph below shows how raw sources, staging models, core dimensions and facts, intermediate models, marts, and data tests are connected.

This image is intended as a high-level visual proof of the modeled dependency graph, not as a detailed reading surface.

![dbt lineage graph](docs/images/dbt_lineage_graph.png)

---

## Core entity relationship diagram

The diagram below summarizes the core dimension and fact join paths.

```mermaid
erDiagram
    DIM_USER ||--o{ FCT_ACCESS_REQUEST : "requester_user_id -> user_id"
    DIM_USER ||--o{ FCT_TOOL_USAGE_DAILY : "user_id -> user_id"

    DIM_TOOL ||--o{ FCT_ACCESS_REQUEST : "tool_code -> tool_code"
    DIM_TOOL ||--o{ FCT_TOOL_USAGE_DAILY : "tool_code -> tool_code"
    DIM_TOOL ||--o{ FCT_TOOL_SPEND_MONTHLY : "tool_code -> tool_code"

    DIM_USER {
        string user_id PK
        string user_name
        string user_email
        string team_name
        string department_name
        string job_level
        string employment_status
    }

    DIM_TOOL {
        string tool_code PK
        string tool_name
        string vendor_name
        string tool_category
        string deployment_scope
        string risk_tier
        boolean is_active
    }

    FCT_ACCESS_REQUEST {
        string request_id PK
        timestamp requested_at_utc
        date requested_month
        string requester_user_id FK
        string tool_code FK
        string request_purpose
        string data_classification
        string request_status
        timestamp reviewed_at_utc
        string reviewed_by_user_id
        float approval_lead_time_hours
    }

    FCT_TOOL_USAGE_DAILY {
        date usage_date PK
        string user_id PK, FK
        string tool_code PK, FK
        integer session_count
        integer prompt_count
        integer input_tokens_total
        integer output_tokens_total
        boolean has_usage_activity
    }

    FCT_TOOL_SPEND_MONTHLY {
        date billing_month PK
        string team_name PK
        string tool_code PK, FK
        string department_name
        integer licensed_seats
        decimal fixed_license_cost_usd
        decimal variable_usage_cost_usd
        decimal spend_usd
    }
```

> Note: Relationships in this ERD represent warehouse-level resolvability and join paths validated by dbt tests. They are not physical database foreign key constraints in DuckDB.

---

## What this project demonstrates

This repository is intended as an analytics engineering portfolio artifact.

It demonstrates the ability to:

- design source contracts for analytical data
- build a layered dbt project
- preserve and document model grain
- separate transformation failures from business review signals
- validate models with generic and singular data tests
- model both stock and flow metrics
- generate reviewer-facing analytical outputs from marts
- document assumptions and scope boundaries clearly
- validate the same dbt model tree on both DuckDB and BigQuery

---

## Data domain

The modeled domain is enterprise artificial intelligence tool access governance.

The synthetic dataset includes:

| Area | Modeled object |
|---|---|
| Tool catalog | Enterprise artificial intelligence tools |
| User directory | Current-state users, teams, departments, and job levels |
| Access requests | Request workflow rows with final review state |
| Usage | Daily user-tool usage activity |
| Spend | Monthly team-tool billing rows |
| Governance exceptions | Current user-tool exception signals |
| Adoption review candidates | Monthly team-tool follow-up signals |

---

## Raw source tables

The generator emits five raw Parquet files under `data/raw/`:

| Raw source | Grain |
|---|---|
| `raw_tool_catalog` | One row per tool |
| `raw_user_directory` | One row per user |
| `raw_access_requests` | One row per access request |
| `raw_usage_events_daily` | One row per user, tool, and day with recorded activity |
| `raw_tool_spend_monthly` | One row per billed month, team, and tool |

The raw files are synthetic, deterministic, and locally reproducible.

---

## dbt model layers

| Layer | Purpose |
|---|---|
| Sources | Define raw Parquet input contracts |
| Staging | Standardize raw fields while preserving raw grain |
| Core | Define reusable dimensions and facts |
| Intermediate | Isolate stock logic, re-graining, and reusable mart support logic |
| Marts | Provide business-facing analytical outputs |

---

## Key marts

The primary business-facing marts are:

| Mart | Grain | Purpose |
|---|---|---|
| `access_requests_monthly` | Reporting month, team, and tool | Request inflow, approval/rejection flow, and month-end backlog |
| `tool_adoption_monthly` | Reporting month, team, and tool | Approved access, monthly usage, spend, and adoption alignment |
| `adoption_review_candidates_monthly` | Reporting month, team, and tool | Monthly adoption, usage, and spend review candidates |
| `governance_exceptions_current` | User and tool | Current approval and recent usage exception review |

---

## Static governance report

The repository includes a generated static governance report:

```text
artifacts/reports/governance_report_v0_2_x.md
```

The report is generated from the dbt mart layer by:

```bash
uv run python scripts/build_governance_report.py
```

The report summarizes:

- request trends
- approval and rejection flow
- tool adoption
- usage and spend alignment
- review candidates
- current governance exceptions

### Report snapshot

The generated report currently summarizes the following mart-level signals:

| Metric | Value |
|---|---:|
| Total access requests | 553 |
| Decision approval rate | 77.1% |
| Latest month-end pending requests | 30 |
| Total sessions | 61,970 |
| Total spend | $153,913.72 |
| Current used-without-approval exceptions | 8 |
| Current approved-but-inactive cases | 24 |

These figures are generated from deterministic synthetic data and should be read as a reproducible portfolio dataset, not as real operational metrics.

The report reads from these mart tables:

```text
main.access_requests_monthly
main.tool_adoption_monthly
main.adoption_review_candidates_monthly
main.governance_exceptions_current
```

The report does not recompute mart-owned business classifications in Python.

---

## BigQuery execution evidence

v0.2.0 adds an optional BigQuery execution path while preserving the local DuckDB path as the primary review path.

The BigQuery path has been validated with:

```bash
uv run dbt build --target bigquery_dev
uv run dbt test --target bigquery_dev
```

Committed cloud execution evidence:

| Artifact | Purpose |
|---|---|
| [`artifacts/cloud/bigquery_build_summary.md`](artifacts/cloud/bigquery_build_summary.md) | Summarizes the BigQuery dbt build result |
| [`artifacts/cloud/bigquery_test_summary.md`](artifacts/cloud/bigquery_test_summary.md) | Summarizes the BigQuery dbt data test result |
| [`artifacts/cloud/bigquery_relation_inventory.md`](artifacts/cloud/bigquery_relation_inventory.md) | Lists BigQuery raw tables and dbt output relations |

The BigQuery path validates the same logical source contract, staging layer, core layer, intermediate layer, and marts used by the local DuckDB path, without maintaining a separate BigQuery-specific model tree.

---

## Looker Studio dashboard artifacts

v0.2.1 adds lightweight Looker Studio dashboard artifacts on top of the BigQuery execution path.

The dashboard connects selected BigQuery mart outputs to embedded Looker Studio data sources and presents them as three stakeholder-facing pages:

| Page | Screenshot |
|---|---|
| Executive Overview | [`docs/assets/looker-studio/executive_overview_dashboard.png`](docs/assets/looker-studio/executive_overview_dashboard.png) |
| Tool Adoption and Usage | [`docs/assets/looker-studio/tool_adoption_dashboard.png`](docs/assets/looker-studio/tool_adoption_dashboard.png) |
| Governance Exceptions and Review Signals | [`docs/assets/looker-studio/governance_exceptions_dashboard.png`](docs/assets/looker-studio/governance_exceptions_dashboard.png) |

Dashboard documentation:

```text
docs/looker-studio-dashboard.md
```

The dashboard uses these existing marts:

```text
access_governance_dbt.access_requests_monthly
access_governance_dbt.tool_adoption_monthly
access_governance_dbt.adoption_review_candidates_monthly
access_governance_dbt.governance_exceptions_current
```

The dashboard is a BI-facing portfolio artifact, not production BI infrastructure. Business logic, review classifications, and mart grain remain owned by dbt. Looker Studio is used for presentation, filtering, charting, and screenshot-based documentation.

A public Looker Studio report link is not required. The repository-facing artifacts are the committed screenshots and documentation.

---

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/ShikiIchitose/access-governance-warehouse.git
cd access-governance-warehouse
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure the dbt profile

```bash
cp profiles/profiles.yml.example profiles/profiles.yml
```

The project is designed to use a local DuckDB database file:

```text
data/warehouse/access_governance.duckdb
```

### 4. Use the committed sample raw data

This repository includes a small deterministic sample raw dataset under:

```text
data/raw/
```

These Parquet files are synthetic, deterministic, and intended as the default local source fixture for quick dbt review.

If you want to regenerate the raw files from the generator, run:

```bash
uv run python -m scripts.generate_synthetic_raw
```

### 5. Inspect generated raw Parquet files

Optionally, inspect the generated raw Parquet files directly with DuckDB before building the dbt warehouse:

```bash
duckdb < scripts/inspect_generated_raw_parquet.sql
```

This inspection script is intended for local sanity checks of the generated raw layer, including row counts, schemas, preview rows, distributions, duplicate smoke checks, and spend-math smoke checks.

It is not the canonical validation mechanism. Generator validation artifacts and dbt tests remain the primary validation surfaces.

### 6. Build the warehouse

```bash
uv run dbt build
```

This runs dbt models and tests in dependency order.

### 7. Generate the static report

```bash
uv run python scripts/build_governance_report.py
```

The generated report is written to:

```text
artifacts/reports/governance_report_v0_2_x.md
```

### Optional: run the BigQuery path

The BigQuery path is optional and requires a Google Cloud project.

See the full guide:

```text
docs/bigquery-execution-path.md
```

Configure the BigQuery dbt target by copying the `bigquery_dev` output from:

```text
profiles/profiles.bigquery.yml.example
```

into your local dbt profile:

```text
~/.dbt/profiles.yml
```

The example uses local OAuth-based Application Default Credentials.

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "${GCP_PROJECT_ID}"
```

After creating the required BigQuery datasets, the committed raw Parquet fixtures can be loaded with:

```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export BQ_LOCATION="asia-northeast1"

uv run python scripts/load_raw_to_bigquery.py \
  --project-id "${GCP_PROJECT_ID}" \
  --location "${BQ_LOCATION}"
```

Then run the dbt BigQuery target:

```bash
uv run dbt build --target bigquery_dev
```

---

## Core commands

### Parse the dbt project

```bash
uv run dbt parse
```

### Run the full dbt build

```bash
uv run dbt build
```

### Run all dbt tests

```bash
uv run dbt test
```

### Run only generic tests

```bash
uv run dbt test --select "test_type:generic"
```

### Run only singular tests

```bash
uv run dbt test --select "test_type:singular"
```

### Inspect generated raw Parquet files

```bash
duckdb < scripts/inspect_generated_raw_parquet.sql
```

### Generate dbt documentation

```bash
uv run dbt docs generate
```

### Serve dbt documentation locally

```bash
uv run dbt docs serve
```

### Generate the static governance report

```bash
uv run python scripts/build_governance_report.py
```

### Load raw Parquet fixtures into BigQuery

```bash
uv run python scripts/load_raw_to_bigquery.py \
  --project-id "${GCP_PROJECT_ID}" \
  --location "${BQ_LOCATION}"
```

### Dry-run the BigQuery raw loading plan

```bash
uv run python scripts/load_raw_to_bigquery.py \
  --project-id "${GCP_PROJECT_ID}" \
  --location "${BQ_LOCATION}" \
  --dry-run
```

### Run the BigQuery dbt build

```bash
uv run dbt build --target bigquery_dev
```

### Run BigQuery dbt tests only

```bash
uv run dbt test --target bigquery_dev
```

---

## Testing strategy

The test suite is designed to validate transformation correctness while allowing legitimate business review signals to appear in marts.

At the current validation baseline, the project includes:

| Test category | Count |
|---|---:|
| Generic tests | 278 |
| Core singular tests | 7 |
| Intermediate singular tests | 12 |
| Mart singular tests | 18 |
| Total data tests | 315 |

### Local validation baseline

A representative local DuckDB `dbt build` completed successfully with the following baseline:

```text
dbt=1.11.8
duckdb=1.10.1
Found 315 data tests, 19 models, 5 sources
Finished running 4 table models, 315 data tests, 15 view models
Done. PASS=334 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=334
```

A representative local DuckDB `dbt test` completed successfully with:

```text
Done. PASS=315 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=315
```

### BigQuery validation baseline

A representative BigQuery `dbt build` completed successfully with the following baseline:

```text
dbt=1.11.8
dbt-bigquery=1.11.1
Found 315 data tests, 19 models, 5 sources
Finished running 4 table models, 315 data tests, 15 view models
Done. PASS=334 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=334
```

A representative BigQuery `dbt test` completed successfully with:

```text
Done. PASS=315 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=315
```

The test strategy distinguishes between:

| Category | Meaning |
|---|---|
| Transformation failure | A structural or logical defect that should fail dbt tests |
| Business review signal | A meaningful analytical condition that should appear in marts |

Examples of transformation failures:

- duplicate rows at a declared grain
- invalid enum-like values
- broken foreign key-like relationships
- negative usage or spend metrics
- failed reconciliation between upstream and downstream models

Examples of business review signals:

- usage without approved access
- approved access without recent usage
- usage without a billing row
- billing without usage
- high-priority review candidates

Business exceptions are outputs. Transformation inconsistencies are failures.

---

## Quality checks

This repository uses a deliberately lightweight CI setup.

Continuous integration currently runs Ruff lint and format checks only. The primary data validation surface is dbt data testing.

Local validation:

```bash
uv run dbt build
uv run dbt test
```

Optional BigQuery validation:

```bash
uv run dbt build --target bigquery_dev
uv run dbt test --target bigquery_dev
```

BigQuery validation requires a Google Cloud project and is documented as an optional cloud execution path rather than a required default CI step.

`pytest` is not used because the main correctness checks are expressed as dbt generic tests, dbt singular tests, and generator validation artifacts.

---

## Repository structure

```text
access-governance-warehouse/
├─ README.md
├─ pyproject.toml
├─ uv.lock
├─ dbt_project.yml
├─ profiles/
│  ├─ profiles.yml.example
│  └─ profiles.bigquery.yml.example
├─ data/
│  ├─ raw/       # committed deterministic synthetic Parquet source files
│  └─ warehouse/ # local DuckDB database output, not committed
├─ models/
│  ├─ sources/
│  ├─ staging/
│  ├─ core/
│  ├─ intermediate/
│  └─ marts/
├─ tests/
│  └─ singular/
├─ scripts/
│  ├─ generate_synthetic_raw.py
│  ├─ inspect_generated_raw_parquet.sql
│  ├─ load_raw_to_bigquery.py
│  └─ build_governance_report.py
├─ generator/
├─ docs/       # modeling docs, BigQuery guide, Looker Studio dashboard docs, and screenshots
└─ artifacts/
   ├─ cloud/
   ├─ reports/
   └─ validation/
```

---

## Documentation map

| Document | Purpose |
|---|---|
| [`docs/domain-modeling-and-assumptions.md`](docs/domain-modeling-and-assumptions.md) | Domain assumptions, model grain, and scope boundaries |
| [`docs/testing-strategy.md`](docs/testing-strategy.md) | Testing philosophy, layer-level coverage, and validation commands |
| [`docs/generator_source_contract_and_design_summary.md`](docs/generator_source_contract_and_design_summary.md) | Compact generator source contract and design summary |
| [`docs/bigquery-execution-path.md`](docs/bigquery-execution-path.md) | Optional BigQuery setup, raw loading, dbt execution, validation, and cleanup guide |
| [`docs/looker-studio-dashboard.md`](docs/looker-studio-dashboard.md) | Looker Studio dashboard purpose, pages, chart inventory, metric definitions, screenshots, limitations, and reproduction notes |
| [`artifacts/reports/governance_report_v0_2_x.md`](artifacts/reports/governance_report_v0_2_x.md) | Generated static governance report |
| [`artifacts/cloud/bigquery_build_summary.md`](artifacts/cloud/bigquery_build_summary.md) | BigQuery dbt build evidence |
| [`artifacts/cloud/bigquery_test_summary.md`](artifacts/cloud/bigquery_test_summary.md) | BigQuery dbt test evidence |
| [`artifacts/cloud/bigquery_relation_inventory.md`](artifacts/cloud/bigquery_relation_inventory.md) | BigQuery raw and dbt relation inventory |

---

## Important modeling assumptions

This repository intentionally uses a bounded analytical model.

Key assumptions:

- The user directory is current-state only.
- Historical organization membership is not modeled.
- Access requests are represented as request-level final-state rows.
- Usage is modeled at daily aggregated grain, not event grain.
- Spend is modeled at monthly team-tool grain.
- Approved access is treated as persistent after approval.
- Revocation is not modeled.
- The dataset is synthetic and deterministic.
- The warehouse is not an audit-grade reconstruction of historical access state.

These assumptions keep the project compact, inspectable, and suitable for a local analytics engineering portfolio.

---

## Grain-aware interpretation

Each dbt model has an explicit grain.

Metrics should be interpreted at the grain of the model that exposes them.

For example, `tool_adoption_monthly` is at reporting month, team, and tool grain. Summing `approved_users_total` across team-tool rows should not be interpreted as a global distinct user count, because the same user can be approved for more than one tool.

When a different grain is required, the warehouse should expose a model or mart at that grain rather than asking the report layer to infer unavailable detail from aggregated rows.

---

## Synthetic generator role

The synthetic generator is a supporting component of this repository.

Its role is to provide deterministic, inspectable, warehouse-ready raw source files.

The primary reviewer-facing value of this repository is in the downstream warehouse work:

- source definitions
- staging models
- dimensions and facts
- intermediate models
- marts
- tests
- dbt documentation
- static governance reporting

The generator should be understood as a source-layer contract provider, not as the main portfolio artifact.

The committed files under `data/raw/` are the default deterministic sample source fixture for quick local review. The generator can be run to reproduce or refresh these files under the current repository configuration.

The committed raw Parquet files are treated as the default sample dataset. Regenerating them should preserve the logical dataset under the same configuration, although file modification times may change.

The repository also includes a DuckDB inspection script for raw Parquet outputs:

```text
scripts/inspect_generated_raw_parquet.sql
```

It can be used for local inspection after raw data generation:

```bash
duckdb < scripts/inspect_generated_raw_parquet.sql
```

This script is an inspection aid. It is not the canonical validation mechanism.

---

## Related project

This warehouse is conceptually aligned with the related Django portfolio project:

[`ai-tool-access-requests`](https://github.com/ShikiIchitose/ai-tool-access-requests)

The related project is a minimal Django application for enterprise artificial intelligence tool access request and approval workflows.

This repository focuses on the downstream analytical warehouse layer that could sit after such an application. It models how access request data, usage activity, and spend data can be transformed into governance, adoption, and review outputs.

This warehouse does not extract live data from the Django application. The raw data in this repository is synthetic, deterministic, and file-based.

The application user interface belongs to the Django repository. This repository focuses on warehouse modeling, dbt transformations, data tests, documentation, and static reporting.

---

## Scope boundaries

This repository is in scope for:

- local DuckDB warehouse modeling
- optional BigQuery warehouse execution validation
- dbt transformations
- deterministic synthetic raw data
- data tests
- dbt documentation
- static Markdown reporting
- committed cloud execution evidence
- lightweight Looker Studio dashboard artifacts
- screenshot-based BI documentation

The following are intentionally outside the scope of this repository:

- production orchestration
- live source extraction
- production-grade cloud deployment
- scheduled dbt jobs
- BigQuery execution in default CI
- application user interface implementation
- real access provisioning
- real audit trails
- slowly changing user dimensions
- access revocation
- audit-grade access reconstruction
- historical organization snapshots
- Terraform-managed infrastructure
- custom dashboard application development
- production BI deployment
- public Looker Studio report link requirement

These exclusions are intentional.  
They keep the project focused on a minimal, reviewable dbt warehouse.

---

## Reviewer guide

Recommended review path:

1. Start with this `README.md`.
2. Open the generated static report:
   - `artifacts/reports/governance_report_v0_2_x.md`
3. Review the Looker Studio dashboard artifacts:
   - `docs/looker-studio-dashboard.md`
   - `docs/assets/looker-studio/executive_overview_dashboard.png`
   - `docs/assets/looker-studio/tool_adoption_dashboard.png`
   - `docs/assets/looker-studio/governance_exceptions_dashboard.png`
4. Review the BigQuery execution evidence:
   - `artifacts/cloud/bigquery_build_summary.md`
   - `artifacts/cloud/bigquery_test_summary.md`
   - `artifacts/cloud/bigquery_relation_inventory.md`
5. Review the mart models:
   - `models/marts/governance/`
6. Review the testing strategy:
   - `docs/testing-strategy.md`
7. Review the domain assumptions:
   - `docs/domain-modeling-and-assumptions.md`
8. Review the optional BigQuery execution guide:
   - `docs/bigquery-execution-path.md`
9. Generate and inspect dbt documentation locally:
   - `uv run dbt docs generate`
   - `uv run dbt docs serve`

---

## Current status

v0.2.1 extends the local DuckDB analytics engineering portfolio and the optional BigQuery execution path with lightweight Looker Studio dashboard artifacts.

The local DuckDB path remains the primary clone-and-run review path. The BigQuery path validates that the same dbt source contract, model tree, marts, and data test suite can run on a cloud data warehouse. The Looker Studio artifacts demonstrate that selected BigQuery marts can support stakeholder-facing BI reporting through documented dashboard screenshots.

Current validation baseline:

```text
DuckDB dbt build:   PASS=334 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=334
DuckDB dbt test:    PASS=315 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=315
BigQuery dbt build: PASS=334 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=334
BigQuery dbt test:  PASS=315 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=315
```

Committed v0.2.1 BI-facing artifacts:

```text
docs/looker-studio-dashboard.md
docs/assets/looker-studio/executive_overview_dashboard.png
docs/assets/looker-studio/tool_adoption_dashboard.png
docs/assets/looker-studio/governance_exceptions_dashboard.png
```

## License

MIT License. See `LICENSE` file.
