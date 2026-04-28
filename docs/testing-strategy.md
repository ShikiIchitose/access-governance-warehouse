# Testing Strategy

This document describes the testing strategy for `access-governance-warehouse` v0.1.0.

The project uses dbt (data build tool) data tests to validate source contracts, staging normalization, dimensional integrity, fact grains, intermediate stock/flow invariants, mart-level reconciliation, and review-candidate classification logic.

The testing strategy is intentionally designed to separate:

1. transformation correctness, which should fail dbt tests when broken
2. business review signals, which should be surfaced as analytical outputs rather than treated as pipeline failures

---

## 1. Testing Goals

The test suite is designed to make the warehouse reliable, explainable, and reviewer-friendly.

The main goals are:

- validate that raw source contracts are structurally usable
- confirm that staging models preserve source grain and normalize low-level fields correctly
- protect reusable dimension keys
- protect fact-table grains and metric validity
- validate intermediate stock/flow logic used by marts
- reconcile mart metrics back to upstream models
- confirm that review-candidate classifications are logically consistent
- avoid brittle tests that depend on exact synthetic row counts

This project is a local warehouse and analytics engineering portfolio project.
Therefore, the test suite emphasizes inspectable correctness and reproducible validation rather than production-scale monitoring.
Production observability, alerting, and incident management are outside the scope of v0.1.0.

---

## 2. Testing Philosophy

### 2.1 What should fail dbt tests

dbt tests should fail when the transformation pipeline is structurally or logically broken.

Examples include:

- missing required keys
- duplicate rows at a declared grain
- invalid enum-like values
- broken foreign key-like relationships
- negative count or spend metrics
- inconsistent boolean helper flags
- broken reconciliation between upstream and downstream layers
- incorrect `review_status`, `review_owner_hint`, or `review_priority` logic

These failures indicate that the warehouse output is no longer trustworthy.

### 2.2 What should not fail dbt tests

Business review signals should not fail dbt tests by themselves.

Examples include:

- rows classified as `finance_review_active_without_billing`
- rows classified as `cost_review_billed_without_usage`
- rows classified as `adoption_review_approved_not_used`
- high-priority review candidates
- changes in the number of `aligned` rows after generator tuning

These rows are analytical outputs. They indicate conditions that should be reviewed by stakeholders, not transformation defects.

For example, a row where usage exists but no billing row is present may be a valid finance/procurement review candidate. It should be surfaced in `adoption_review_candidates_monthly`, not treated as a failed dbt test.

---

## 3. Test Categories

The project uses two broad categories of dbt data tests:

1. generic tests
2. singular tests

### 3.1 Generic tests

Generic tests are declared in YAML files and are used for common structural checks.

The project uses the following generic test patterns:

- `not_null`
- `unique`
- `relationships`
- `accepted_values`

Generic tests are used when the assertion is column-level or follows a common dbt testing pattern.

Examples:

- primary business keys are not null
- primary business keys are unique
- enum-like fields contain only accepted values
- foreign key-like identifiers resolve to the expected upstream dimension or source table
- required metric columns are populated

In this project, `relationships` tests are interpreted as resolvability checks. They confirm that a foreign key-like value can join to the referenced source or dimension. They do not imply that the tested model was constructed from the referenced model.

The project uses the dbt `arguments:` style for generic test configuration.

Example:

```yaml
data_tests:
  - accepted_values:
      arguments:
        values:
          - low
          - medium
          - high
```

Block-style YAML lists are preferred for readability and cleaner Git diffs.

### 3.2 Singular tests

Singular tests are SQL files under `tests/singular/`.

They are used when the assertion requires custom SQL logic, cross-column logic, reconciliation, or grain-level validation that is clearer as a query.

Examples:

- composite grain uniqueness
- non-negative metric checks across multiple columns
- spend component reconciliation
- monthly usage reconciliation
- approved-access stock monotonicity
- mart-level row-count or metric reconciliation
- review-candidate routing and priority consistency

A singular test should return zero rows when the assertion passes.

---

## 4. Layer-Level Coverage

The test suite follows the warehouse layer structure:

```text
raw sources
  -> staging
  -> core
  -> intermediate
  -> marts
```

Each layer has a different testing responsibility.

---

## 5. Source Tests

Source tests validate the raw input contract.

Source file:

```text
models/sources/sources.yml
```

Command:

```bash
uv run dbt test --select "source:access_governance,test_type:generic"
```

The source tests validate:

- raw primary keys are present and unique where appropriate
- raw enum-like values are in accepted sets
- raw user and tool references resolve to source tables
- nullable review-side fields are not incorrectly tested as `not_null`

The source layer represents deterministic synthetic raw Parquet files generated for this project. Source tests validate the raw contract exposed to dbt; they do not validate every generator implementation detail.

Generator-side QA remains responsible for validating deterministic emission, raw file presence, exact raw column order, row-count observability, and generator-specific business-rule realization.

---

## 6. Staging Tests

Staging tests validate source-conformed cleanup.

File:

```text
models/staging/access_governance/schema.yml
```

Command:

```bash
uv run dbt test --select "path:models/staging/access_governance,test_type:generic"
```

The staging tests validate:

- staging keys are preserved
- normalized enum-like values remain valid
- helper boolean columns are populated
- required staging metrics are not null
- nullable review-side fields remain intentionally nullable

The staging layer does not join or aggregate data. Its tests focus on preserving raw grain while normalizing names, types, timestamps, and simple helper fields.

---

## 7. Core Tests

Core tests validate reusable dimensions and facts.

File:

```text
models/core/schema.yml
```

Command:

```bash
uv run dbt test --select "path:models/core,test_type:generic"
```

The core generic tests validate:

- `dim_tool.tool_code` is not null and unique
- `dim_user.user_id` is not null and unique
- `dim_user.user_email` is unique
- `fct_access_request.request_id` is not null and unique
- core fact keys resolve to reusable dimensions
- core enum-like values remain valid

Core singular tests validate:

- final request statuses have the expected review-side fields
- approval lead time is non-negative
- usage fact grain is unique
- usage metrics are non-negative
- spend fact grain is unique
- spend metrics are non-negative
- spend components reconcile to total spend

Core models define the reusable warehouse semantics. Therefore, the tests focus on dimensional keys, fact grains, metric validity, and relationship integrity.

---

## 8. Intermediate Tests

Intermediate tests validate re-graining, stock logic, and reusable mart support logic.

File:

```text
models/intermediate/governance/schema.yml
```

Command:

```bash
uv run dbt test --select "path:models/intermediate/governance,test_type:generic"
```

Singular tests:

```bash
uv run dbt test --select "path:tests/singular/intermediate,test_type:singular"
```

The intermediate layer contains purpose-built models for:

- current approved-access state
- recent 30-day usage state
- month-end open request backlog
- approved-access stock as of month end
- monthly usage aggregated to team and tool

Intermediate tests validate:

- declared grains are unique
- required keys are populated
- user and tool references resolve correctly
- helper flags are logically consistent
- recent 30-day windows are valid
- open request rows truly represent month-end backlog
- approved-access rows are effective as of month end
- approved-access stock is monotonic while revocation is not modeled
- monthly usage totals reconcile to daily usage facts

The intermediate layer is not a business-facing output layer. Its purpose is to keep mart SQL readable by isolating reusable state, windowing, stock, and aggregation logic.

---

## 9. Mart Tests

Mart tests validate business-facing analytical outputs.

File:

```text
models/marts/governance/schema.yml
```

Command:

```bash
uv run dbt test --select "path:models/marts/governance,test_type:generic"
```

Singular tests:

```bash
uv run dbt test --select "path:tests/singular/marts,test_type:singular"
```

The mart layer includes:

- `access_requests_monthly`
- `tool_adoption_monthly`
- `adoption_review_candidates_monthly`
- `governance_exceptions_current`

Mart tests validate:

- mart grains are unique
- required reporting fields are populated
- request metrics are non-negative
- usage metrics reconcile to upstream monthly usage aggregation
- spend metrics reconcile to the spend fact
- approved-user stock reconciles to the approved-access intermediate model
- backlog totals reconcile to the month-end open request intermediate model
- exception flags are logically consistent
- review candidate classifications are logically consistent
- review owner hints are logically consistent
- review priorities are logically consistent

Mart tests are designed to validate the correctness of business-facing outputs without suppressing legitimate review signals.

---

## 10. Business Review Signals vs Test Failures

The project intentionally distinguishes analytical findings from data transformation failures.

### 10.1 Analytical findings

The following conditions are valid business review signals:

- usage exists without approved access
- approved access exists without recent usage
- usage exists without a billing row
- billing exists without usage
- a high-risk tool appears in a high-priority review candidate row

These are expected to appear in marts such as:

- `governance_exceptions_current`
- `adoption_review_candidates_monthly`

They should be reviewed by stakeholders, but their existence does not mean the dbt pipeline is broken.

### 10.2 Transformation failures

The following conditions should fail tests:

- duplicate rows at a declared grain
- invalid `review_status` values
- invalid `review_priority` values
- missing required keys
- negative metrics
- broken source-to-staging or fact-to-dimension relationships
- reconciliation mismatches between mart metrics and upstream models
- a `review_status` value that does not match the presence flags used to derive it

In this document, a business exception means a condition that should be reviewed by a stakeholder, not necessarily a data defect.

The principle is:

```text
Business exceptions are outputs.
Transformation inconsistencies are failures.
```

---

## 11. Avoiding Brittle Row-Count Tests

The synthetic generator may be tuned over time.

For example, the number of billed spend rows may change when spend-generation parameters are adjusted. Tests should not hard-code generator-dependent row counts unless the count is part of a stable source contract.

Avoid tests such as:

```text
raw_tool_spend_monthly row count = 313
aligned row count = 313
finance_review_active_without_billing row count = 28
```

Prefer reconciliation tests such as:

```text
mart rows with spend_usd is not null
=
fct_tool_spend_monthly rows
```

or:

```text
mart metric total
=
upstream metric total
```

This keeps tests robust when the synthetic generator is intentionally tuned while still validating transformation correctness.

---

## 12. Validation Baseline

At the current v0.1.0 validation baseline, the test suite contains:

| Test category | Count |
|---|---:|
| Generic tests | 278 |
| Core singular tests | 7 |
| Intermediate singular tests | 12 |
| Mart singular tests | 18 |
| Total data tests | 315 |

The current validation baseline covers:

| Object type | Count |
|---|---:|
| View models | 15 |
| Table models | 4 |
| Data tests | 315 |

The current baseline build passes with 334 total nodes, including 15 view models, 4 table models, and 315 data tests.

---

## 13. Recommended Commands

### Parse the project

```bash
uv run dbt parse
```

### Run the full build

`dbt build` is the preferred end-to-end validation command because it runs models and tests together in dependency order.

```bash
uv run dbt build
```

### Run all tests

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

### Run source generic tests

```bash
uv run dbt test --select "source:access_governance,test_type:generic"
```

### Run layer-specific generic tests

```bash
uv run dbt test --select "path:models/staging/access_governance,test_type:generic"
uv run dbt test --select "path:models/core,test_type:generic"
uv run dbt test --select "path:models/intermediate/governance,test_type:generic"
uv run dbt test --select "path:models/marts/governance,test_type:generic"
```

### Run layer-specific singular tests

```bash
uv run dbt test --select "path:tests/singular/core,test_type:singular"
uv run dbt test --select "path:tests/singular/intermediate,test_type:singular"
uv run dbt test --select "path:tests/singular/marts,test_type:singular"
```

### Generate dbt documentation

```bash
uv run dbt docs generate
uv run dbt docs serve
```

---

## 14. How to Inspect Failures

When a dbt test fails, inspect the failure by asking three questions.

### 14.1 Is the failure structural?

Examples:

- duplicate key
- null required key
- invalid enum value
- broken relationship

These usually indicate a source contract issue, transformation issue, or test definition issue.

### 14.2 Is the failure a reconciliation mismatch?

Examples:

- mart total does not match upstream fact total
- spend component total does not match `spend_usd`
- monthly aggregation does not reconcile to daily facts

These usually indicate a transformation bug or a changed upstream grain assumption.

### 14.3 Is the failure actually a business review signal?

Examples:

- active usage without billing
- approved access without usage
- billing without usage

These should normally be surfaced in marts, not implemented as failing tests.

If a business review signal appears as a failing test, first check whether the test is actually protecting transformation correctness. If the test is only blocking a valid review candidate from appearing in a mart, the test should be reworked or removed.

---

## 15. Future Maintenance Notes

### 15.1 If revocation is introduced

Revisit tests that assume approved access is persistent.

In particular, approved-access stock may legitimately decrease if access revocation is modeled. Tests that currently expect monotonic approved stock should be revised.

### 15.2 If historical organization snapshots are introduced

Revisit models and tests that rely on current-state user attribution.

Affected areas may include:

- request attribution
- usage attribution
- approved-user stock by team
- monthly adoption marts

### 15.3 If the warehouse backend changes

If the project moves away from DuckDB, revisit exact equality checks involving decimal and ratio metrics.

Potentially affected areas include:

- spend component reconciliation
- cost-per-active-user consistency
- rounded monetary comparisons

### 15.4 If generator parameters are tuned

Avoid adding tests that depend on incidental synthetic row counts.

Prefer:

- grain validation
- relationship validation
- enum validation
- metric non-negativity
- upstream/downstream reconciliation
- classification logic validation

---

## 16. Summary

The test suite validates that the warehouse transformation pipeline is structurally sound and analytically consistent.

It is designed to protect:

- source contracts
- staging normalization
- core dimensional integrity
- fact grains
- intermediate stock/flow invariants
- mart reconciliation
- review-candidate classification logic

At the same time, it intentionally allows business review candidates to appear in marts. These candidates are part of the analytical value of the project, not test failures.
