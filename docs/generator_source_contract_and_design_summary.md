# Generator Source Contract and Design Summary

> 日本語版: [generator_source_contract_and_design_summary.ja.md](generator_source_contract_and_design_summary.ja.md)

## 1. Purpose

This document defines the contract-level summary of the synthetic raw generator used in `access-governance-warehouse` v0.1.0.

It is not the full generator specification.
Its purpose is to state, at a compact level:

- what the generator emits
- which structural guarantees the emitted raw layer is expected to satisfy
- which deterministic and weighted generation rules shape the dataset
- what the generator includes in v0.1.0 and what it intentionally leaves out
- how the emitted raw layer is intended to support the downstream DuckDB + dbt warehouse

The generator is a supporting component of the repository.
Its role is to provide a deterministic, inspectable, and warehouse-ready raw source layer.

The emitted raw layer is intended to approximate source data that could accumulate in a SaaS-like internal AI tool access request and approval application.

## 2. Repository role

Within this repository, the primary reviewer-facing value is in the downstream warehouse work:

- source definitions
- staging models
- dimensions and facts
- marts
- tests
- dbt docs
- static governance reporting

Accordingly, the generator should be treated as a raw source-contract provider for the warehouse layer, not as the main portfolio artifact.

## 3. Deliverables

For v0.1.0, the generator emits exactly five raw Parquet files under `data/raw/`:

- `raw_tool_catalog.parquet`
- `raw_user_directory.parquet`
- `raw_access_requests.parquet`
- `raw_usage_events_daily.parquet`
- `raw_tool_spend_monthly.parquet`

These files are the generator's primary deliverables.

The local DuckDB file at `data/warehouse/access_governance.duckdb` is a downstream warehouse artifact used for SQL and dbt execution. It is not a generator deliverable.

## 4. Raw source contract

### 4.1 Declared grains

The emitted raw layer preserves the following table grains:

- `raw_tool_catalog`: one row per tool
- `raw_user_directory`: one row per user
- `raw_access_requests`: one row per access request
- `raw_usage_events_daily`: one row per user × tool × day
- `raw_tool_spend_monthly`: one row per month × team × tool

These grains are part of the source contract and are not implementation-optional.

### 4.2 Default v0.1.0 row-count targets

For the default v0.1.0 setup, the generator is configured around the following row-count targets:

- `raw_tool_catalog`: 5
- `raw_user_directory`: 198
- `raw_access_requests`: 553
- `raw_usage_events_daily`: 30000
- `raw_tool_spend_monthly`: 313

These targets are part of the intended dataset shape for the default local run configuration.  
Observed runs are expected to align with these targets, with documented acceptance ranges applied where the generator design defines them.

### 4.3 Structural guarantees

The generator is intended to preserve the following raw-layer guarantees:

- deterministic row ordering
- canonical column ordering
- resolvable cross-table references
- raw-grain uniqueness
- status-aware nullability
- non-negative count-like metrics
- UTC timestamp generation
- month fields stored as the first calendar day of the month
- USD monetary values quantized to 2 decimal places
- inactive-user exclusion from requester, reviewer, and usage eligibility where applicable

## 5. Reproducibility model

The generator is designed to be:

- deterministic
- inspectable
- reproducible
- business-rule-driven
- locally runnable

For v0.1.0, reproducibility is anchored by the following fixed settings:

- fixed seed: `18790314`
- fixed anchor month: `2025-12-01`
- fixed reporting window: 12 months

The generator does not use the runtime system clock to alter output content.

### 5.1 Re-run behavior

The generator rewrites raw Parquet files on each run, so file modification times may change even when the generated logical table contents remain unchanged.

With the generator configuration currently committed to this repository, and under the same seed, implementation, and dependency environment, the expected contract is logical output stability.

For reproducibility checks, file modification time should not be used as evidence of data changes. Prefer canonical logical exports or validation artifacts.

For example, `raw_access_requests` produced the same SHA-256 hash across repeated canonical CSV exports under the same generation conditions:

```text
74be333534f543785057bbbe656406f9fc59592a4b7617e551ee5760581d4fea
```

If the generator configuration is intentionally changed, logical output changes are expected and should be treated as a new generated dataset baseline.

## 6. Generation model

The generator is rule-based rather than unconstrained-random.

The normative generation order is:

1. entity setup
2. request volume
3. request context
4. review outcome
5. usage
6. spend

This ordering is intentional.
It gives the downstream warehouse a more coherent relationship structure across requests, approvals, usage, and spend.

## 7. Weighted and Conditional Generation Policy

The v0.1.0 generator uses deterministic weighted allocation and normalized conditional generation rather than fully independent row-wise random sampling.

This policy is intentional.
It preserves a more interpretable relationship across request workflow, observed usage, and spend while keeping the emitted raw layer reproducible under a fixed seed and configuration.

### 7.1 Request generation

Request generation is count-driven first and field-enriched second.

At a contract level, request rows are constructed by:

1. fixing annual team request targets
2. allocating those targets across months using seasonality weights
3. allocating month × team counts across tools using team × tool weights
4. expanding the resulting exact counts into deterministic request-row skeletons
5. enriching the skeletons with request context and review outcome

A compact way to summarize the count-allocation shape is:

```math
N_{m,t,k} \;\propto\; R_t \cdot s_m \cdot p_{t,k}
\qquad (1)
```

where

- $N_{m,t,k}$: allocated request count for month $m$, team $t$, and tool $k$
- $R_t$: annual request target for team $t$
- $s_m$: month seasonality weight for month $m$
- $p_{t,k}$: team × tool request propensity for team $t$ and tool $k$

After weighted allocation, integer row counts are reconciled deterministically so that the final request totals remain aligned with the configured targets.

Review outcome is also weighted rather than flat.
Within the reviewed subset, approval likelihood is conditioned on request context and tool risk:

```math
P(\mathrm{approve}\mid \mathrm{reviewed}, p, c, r)
=
b_p \, m_c \, n_r
\qquad (2)
```

where

- $P(\mathrm{approve}\mid \mathrm{reviewed}, p, c, r)$: approval probability conditional on the request being reviewed
- $p$: `request_purpose`
- $c$: `data_classification`
- $r$: `risk_tier`
- $b_p$: purpose-specific base approval probability
- $m_c$: classification-specific approval multiplier
- $n_r$: risk-tier approval multiplier

Pending is not generated as a flat third status draw.
Instead, pending backlog is controlled separately as a month-end stock design, while reviewed outcomes are shaped by the weighted approval model.

### 7.2 Usage generation

Usage generation is derived from finalized request outcomes rather than sampled independently from request workflow.

At a contract level, the generator first derives the relevant current-state user-tool sets, including:

- approved-current pairs
- approved-active pairs with recent usage
- approved-current pairs without recent usage
- controlled anomaly pairs representing `used_without_approval`

Here, “without recent usage” refers to pair activity state, not to inactive users.
Inactive users remain excluded from emitted usage rows.

This means the emitted usage layer is designed to correlate with approval state while still permitting a bounded exception surface.

At daily grain, usage-date realization follows weighted selection over eligible calendar dates rather than uniform date assignment.
A compact expression of that selection rule is:

```math
S^{\mathrm{usage\_date}}_{i,m,d}
=
\alpha_{w(d)}
\,
\beta_{b(d,m)}
\,
\varepsilon_{i,m,d}
\qquad (3)
```

where

- $S^{\mathrm{usage\_date}}_{i,m,d}$: date-selection score for pair-month-date candidate $(i,m,d)$
- $i$: user-tool pair
- $m$: reporting month
- $d$: candidate calendar date
- $w(d)$: weekday of date $d$
- $b(d,m)$: month-position bucket of date $d$ inside month $m$
- $\alpha_{w(d)}$: weekday multiplier
- $\beta_{b(d,m)}$: month-position multiplier
- $\varepsilon_{i,m,d}$: deterministic jitter for candidate $(i,m,d)$

These scores are interpreted as selection weights, not independent Bernoulli probabilities.

For normal approved pairs, eligible dates are also constrained by approval-effective timing so that normal usage does not appear before approval becomes effective.
Controlled anomaly pairs are handled separately under their own bounded selection logic.

### 7.3 Spend generation

Spend generation is constructed from billed month × team × tool states rather than sampled independently from request or usage rows.

At a contract level, spend realization includes:

1. determining which billed month × team × tool rows exist
2. realizing contract activation timing
3. realizing seat-related contract state
4. deriving fixed and variable spend components
5. deriving total spend and applying monetary rounding

The intended contract-level relationship is that spend correlates with both seat state and observed usage.

A compact summary of the spend-side composition is:

```math
\mathrm{spend\_usd}_{m,t,k}
=
\mathrm{fixed\_license\_cost\_usd}_{m,t,k}
+
\mathrm{variable\_usage\_cost\_usd}_{m,t,k}
\qquad (4)
```

where

- $`\mathrm{spend\_usd}_{m,t,k}`$: total spend for billing month $m$, team $t$, and tool $k$
- $`\mathrm{fixed\_license\_cost\_usd}_{m,t,k}`$: fixed recurring license cost component
- $`\mathrm{variable\_usage\_cost\_usd}_{m,t,k}`$: usage-driven variable cost component

At a higher-level contract abstraction, the variable component is intended to depend on usage intensity and seat-related billing state:

```math
\mathrm{variable\_usage\_cost\_usd}_{m,t,k}
=
f\!\left(
U_{m,t,k},
L_{m,t,k}
\right)
\qquad (5)
```

where

- $U_{m,t,k}$: usage intensity for billing month $m$, team $t$, and tool $k$
- $L_{m,t,k}$: seat-related or contract-related billing state for billing month $m$, team $t$, and tool $k$
- $f(\cdot)$: deterministic cost-realization function under the configured spend model

In v0.1.0, monetary outputs are quantized to 2 decimal places before emission, and final cross-table validation requires:

```math
\mathrm{spend\_usd}
=
\mathrm{fixed\_license\_cost\_usd}
+
\mathrm{variable\_usage\_cost\_usd}
\qquad (6)
```

for every emitted spend row.

### 7.4 Contract interpretation

This section should be read as a contract-level summary of the generator's weighted design.

It does not attempt to reproduce the full implementation detail of all builder modules.
Instead, it records the intended shape of the generation policy:

- request rows are allocated by weighted count planning and context-aware review rules
- usage rows are derived from approval-aware pair states plus controlled anomalies
- spend rows are derived from billed contract state and usage-correlated cost realization

Accordingly, the emitted raw layer is intentionally neither uniformly random nor fully independent across tables.
It is a deterministic synthetic business dataset shaped by weighted business rules.

## 8. Simplifying assumptions

The v0.1.0 source contract is intentionally bounded by a minimal business model.

The main simplifying assumptions are:

- the user directory is current-state only
- organizational history is not modeled
- access requests are represented as request-level rows with final workflow state at extract time
- usage is modeled at daily aggregated grain, not event grain
- spend is modeled at monthly team × tool grain
- approved-access persistence is assumed for downstream current-state logic
- revocation history is not modeled in v0.1.0

These assumptions are intentional.
They keep the emitted raw layer compact, inspectable, and suitable for a minimal warehouse portfolio.

## 9. Validation boundary

Generator outputs are validated before and after write.

The validation boundary includes:

- table-local QA
- cross-table QA
- schema-realization QA
- raw output existence checks
- validation artifact existence checks

The canonical validation artifacts are:

- `artifacts/validation/generator_validation_summary.md`
- `artifacts/validation/generator_validation_summary.json`

These artifacts should be treated as the primary evidence that the emitted raw layer satisfies the intended source contract.

## 10. Inspection support

The repository also includes a DuckDB-oriented inspection script:

- `scripts/inspect_generated_raw_parquet.sql`

Its role is to support direct inspection of the generated raw files, including:

- row counts
- schema
- preview rows
- distributions
- time ranges
- duplicate smoke checks
- spend-math smoke checks

This script is an inspection aid.
It is not the canonical validation mechanism.

## 11. Downstream warehouse interface

The emitted raw layer is intended to act as the stable upstream interface for the downstream DuckDB + dbt warehouse.

In particular, it is designed to support:

- explicit source definitions
- source-level tests
- staging models with stable upstream assumptions
- dimension and fact construction
- marts for access-governance business questions
- lineage and documentation review

The downstream warehouse is intended to answer questions such as:

- Which teams request, approve, or reject which tools over time?
- Are approved tools actually used?
- Which user-tool relationships show usage without approved access?
- Is spend directionally aligned with adoption and usage?

Accordingly, the generator should be understood as a source-layer contract for warehouse modeling, not as an end-user deliverable.

## 12. Navigation

For the lightweight generator overview, see:

- [`generator/README.md`](../generator/README.md)

For the full repository overview, see:

- [`README.md`](../README.md)
