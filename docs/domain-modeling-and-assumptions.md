# Domain Modeling and Assumptions

This document describes the domain modeling choices and simplifying assumptions for `access-governance-warehouse` v0.1.0.

The project is a local warehouse and analytics engineering portfolio project focused on access governance for enterprise AI tools. It is designed to demonstrate explicit warehouse modeling, dbt-based transformation, data quality testing, documentation, lineage, and business-facing analytical outputs.

The goal is not to reproduce a full production access governance platform. Instead, the goal is to provide a minimal but credible warehouse model that can answer a focused set of governance, adoption, usage, and spend questions.

---

## 1. Domain Scope

The modeled domain is enterprise AI tool access governance.

The warehouse focuses on the following business questions:

1. Which teams request, approve, or reject which tools over time?
2. Are approved tools actually used?
3. Which user-tool relationships show usage without approved access?
4. Is spend directionally aligned with adoption and usage?

The domain is intentionally scoped to the analytical warehouse layer. It does not include a product application, approval UI, production orchestration, live extraction, or cloud data warehouse deployment.

### Related application context

This warehouse is conceptually aligned with the related
[`ai-tool-access-requests`](https://github.com/ShikiIchitose/ai-tool-access-requests)
portfolio project, a minimal Django application for enterprise AI tool access
request and approval workflows.

In this repository, however, the raw data is synthetic and file-based. The
warehouse does not extract live data from that application in v0.1.0. Instead,
it models the kind of analytical layer that could sit downstream of an access
request application and related usage and spend sources.

The application UI belongs to the related Django application repository; this
repository focuses on the downstream warehouse and analytical modeling layer.

---

## 2. Modeled Business Entities

The v0.1.0 warehouse models the following primary entities and processes:

| Area | Modeled object | Primary purpose |
|---|---|---|
| Tool catalog | Enterprise AI tools | Defines the tool universe used across requests, usage, spend, and governance reporting |
| User directory | Current-state users | Provides user, team, department, job level, and employment status attributes |
| Access requests | Request workflow rows | Captures submitted access requests and final review state |
| Usage | Daily user-tool usage | Captures observed daily activity for approved or unapproved tool usage analysis |
| Spend | Monthly team-tool spend | Captures billed tool spend at monthly team-tool grain |
| Governance exceptions | User-tool review signals | Surfaces usage without approval and approval without recent usage |
| Adoption review candidates | Monthly team-tool review signals | Surfaces approval, usage, and spend alignment issues |

---

## 3. Layering Model

The warehouse follows a layered dbt model structure:

| Layer | Purpose |
|---|---|
| Sources | Define raw Parquet input contracts |
| Staging | Standardize raw fields while preserving raw grain |
| Core | Define reusable dimensions and facts |
| Intermediate | Isolate re-graining, stock logic, and reusable mart support logic |
| Marts | Provide business-facing analytical outputs |

The intended flow is:

```text
raw sources -> staging -> core -> intermediate -> marts
```

This layering keeps low-level source cleanup separate from reusable warehouse semantics and business-facing outputs.

---

## 4. Source Data Assumptions

The raw layer consists of deterministic synthetic Parquet files generated for this project.

The five raw source tables are:

| Source | Grain |
|---|---|
| `raw_tool_catalog` | One row per tool |
| `raw_user_directory` | One row per user |
| `raw_access_requests` | One row per access request |
| `raw_usage_events_daily` | One row per user, tool, and day with recorded activity |
| `raw_tool_spend_monthly` | One row per billed month, team, and tool |

The raw files are treated as source contracts for dbt. The warehouse validates source-level structure, accepted values, key presence, uniqueness where appropriate, and foreign key-like resolvability.

Generator-side QA remains responsible for validating deterministic emission, raw file presence, exact raw column order, row-count observability, and generator-specific business-rule realization.

---

## 5. Model Grain Overview

Each downstream dbt model is designed with an explicit grain. The grain defines what one row represents and determines which questions can be answered safely from that model.

### Staging models

Staging models preserve the grain of their upstream raw source. They standardize field names, types, and lightweight row-level helper fields, but they do not join or aggregate data.

| Model | Grain |
|---|---|
| `stg_access_governance__tool_catalog` | One row per tool |
| `stg_access_governance__user_directory` | One row per user |
| `stg_access_governance__access_requests` | One row per access request |
| `stg_access_governance__usage_events_daily` | One row per user, tool, and usage date |
| `stg_access_governance__tool_spend_monthly` | One row per billed month, team, and tool |

### Core models

Core models define reusable dimensions and facts. Dimensions are entity-grained, while facts preserve the grain of the business process or measure they represent.

| Model | Grain |
|---|---|
| `dim_tool` | One row per tool |
| `dim_user` | One row per user |
| `fct_access_request` | One row per access request |
| `fct_tool_usage_daily` | One row per user, tool, and usage date |
| `fct_tool_spend_monthly` | One row per billed month, team, and tool |

### Intermediate models

Intermediate models isolate re-graining, stock logic, and reusable mart support logic. They are not end-user-facing outputs.

| Model | Grain |
|---|---|
| `int_access_requests_open_at_month_end` | One row per reporting month and open access request |
| `int_tool_usage_aggregated_to_month_team_tool` | One row per reporting month, team, and tool |
| `int_user_tool_approved_current` | One row per user and tool |
| `int_user_tool_approved_as_of_month_end` | One row per reporting month, user, and tool |
| `int_user_tool_recent_usage_30d` | One row per user and tool with recent usage activity |

### Mart models

Marts are business-facing analytical outputs. Their grain determines the level at which report metrics should be interpreted.

| Model | Grain |
|---|---|
| `access_requests_monthly` | One row per reporting month, team, and tool |
| `tool_adoption_monthly` | One row per reporting month, team, and tool |
| `adoption_review_candidates_monthly` | One row per reporting month, team, and tool |
| `governance_exceptions_current` | One row per user and tool |

### Implication

Metrics should be interpreted at the grain of the model that exposes them. If a business question requires a different grain, the warehouse should expose a model or mart at that grain rather than relying on a downstream report to infer unavailable detail from aggregated rows.

---

## 6. Current-State User Directory Assumption

The user directory is modeled as current-state only.

This means:

- `dim_user` contains the user's current team and department
- request and usage attribution use current-state user attributes
- historical team membership is not reconstructed
- slowly changing dimension behavior is not modeled in v0.1.0

This is a deliberate simplification.

For example, if a user is currently in the Analytics team, historical usage by that user is attributed to Analytics even if the user might have belonged to another team in a real production system.

This makes the model easier to inspect and keeps v0.1.0 focused on warehouse modeling rather than historical organization modeling.

### Implication

Metrics grouped by team or department should be interpreted as current-state attribution, not as-of-event historical attribution.

---

## 7. Access Request Modeling Assumption

Access requests are modeled as request-level final-state rows.

Each row in `raw_access_requests` and `fct_access_request` represents one access request.

A request has:

- requester-side context
- requested tool
- request purpose
- data classification
- final request status
- review-side fields when reviewed

The supported request statuses are:

- `approved`
- `rejected`
- `pending`

Review-side fields are status-aware:

| Status | `reviewed_at` | `reviewed_by_user_id` | `review_comment_text` |
|---|---|---|---|
| `approved` | populated | populated | optional |
| `rejected` | populated | populated | populated |
| `pending` | null | null | null |

This means null review fields for pending requests are intentional workflow state, not missing data.

---

## 8. Approval Persistence and Revocation Assumption

Revocation is not modeled in v0.1.0.

Once a user-tool pair has an approved request, approved access is treated as persistent for downstream current-state and month-end stock logic.

This affects models such as:

- `int_user_tool_approved_current`
- `int_user_tool_approved_as_of_month_end`
- `tool_adoption_monthly`
- `governance_exceptions_current`

### Implication

Approved-access stock can accumulate over time. Tests and marts may assume approved access does not decrease unless a future version introduces revocation.

If revocation is introduced later, approved-access stock logic and tests that assume monotonicity should be revisited.

---

## 9. Usage Modeling Assumption

Usage is modeled at daily aggregated grain, not event grain.

The usage fact grain is:

| Model | Grain |
|---|---|
| `fct_tool_usage_daily` | One row per user, tool, and usage date |

The raw generator emits usage rows only for user-tool-day combinations with recorded activity. Zero-activity combinations are not materialized as raw rows.

Usage metrics include:

- `session_count`
- `prompt_count`
- `input_tokens_total`
- `output_tokens_total`

The warehouse uses these metrics to derive:

- monthly team-tool usage
- active user counts
- recent 30-day usage state
- governance exception signals

### Implication

The absence of a usage row does not mean a generated zero row exists. It means no recorded activity was materialized for that user-tool-day combination.

---

## 10. Recent Usage Window Assumption

Recent usage is defined as a 30-day window.

The recent usage window is anchored to the maximum available `usage_date` in the warehouse, not to the system clock.

This makes the project reproducible because the result does not depend on the day the project is run locally.

The recent usage logic is used by:

- `int_user_tool_recent_usage_30d`
- `governance_exceptions_current`

### Implication

Recent usage should be interpreted relative to the generated dataset, not relative to today's real-world date.

---

## 11. Spend Modeling Assumption

Spend is modeled at monthly team-tool grain.

The spend fact grain is:

| Model | Grain |
|---|---|
| `fct_tool_spend_monthly` | One row per billed month, team, and tool |

Spend rows represent billed combinations only.

This means that not every possible month, team, and tool combination is expected to appear in `raw_tool_spend_monthly` or `fct_tool_spend_monthly`.

A missing spend row can be meaningful when joined into a reporting spine. For example, a mart row may show usage activity but no billing row. That condition can be surfaced as a finance or procurement review candidate.

### Implication

In raw spend and spend facts, existing spend rows should have non-null spend fields.

In marts, `spend_usd`, `licensed_seats`, or `cost_per_active_user` may be null when no billing row exists for the reporting month, team, and tool combination.

---

## 12. Tool Risk Tier Assumption

`risk_tier` is a synthetic governance attribute.

It is used as review context inside the synthetic access governance domain. It should not be interpreted as an objective product-safety assessment of any real-world vendor or tool.

In v0.1.0, `risk_tier` is used to support:

- review strictness
- approval behavior
- review routing
- prioritization of review candidates

### Implication

A high-risk tool in this dataset means the synthetic governance model treats the tool as requiring stricter review. It does not make a claim about the real product.

---

## 13. Data Classification Assumption

`data_classification` represents the highest expected sensitivity of data involved in the requested use case.

The supported values are:

- `public`
- `internal`
- `confidential`
- `restricted`

This classification is generated as part of the synthetic request context and is used by approval and review logic.

### Implication

`data_classification` should be read as a simplified governance input. It is not a full enterprise data classification policy implementation.

---

## 14. Tool Adoption Modeling Assumption

Tool adoption is treated as an operational proxy, not as a direct measure of productivity impact.

In this project, adoption is evaluated through observable warehouse signals such as:

- approved users
- active users
- sessions
- prompts
- spend
- cost per active user

The main monthly adoption mart is:

- `tool_adoption_monthly`

This mart compares approved-access stock, monthly usage flow, and monthly spend flow.

### What adoption means here

In this project, tool adoption means that approved tool access becomes observable team-level usage, with spend reviewed as supporting context.

### What adoption does not mean here

The project does not directly measure:

- productivity improvement
- feature-level proficiency
- user satisfaction
- task quality improvement
- cost savings caused by the tool

Those would require additional product analytics, survey, workflow, or business outcome data that is outside the scope of v0.1.0.

---

## 15. Business Review Signal Assumption

Some modeled conditions are expected analytical outputs, not pipeline failures.

Examples include:

- usage exists without approved access
- approved access exists without recent usage
- usage exists without a billing row
- billing exists without usage
- high-priority review candidates exist

These are surfaced in marts such as:

- `governance_exceptions_current`
- `adoption_review_candidates_monthly`

Spend-usage mismatches should be interpreted as review candidates, not as
confirmed accounting or billing errors.

### Principle

Business exceptions are outputs. Transformation inconsistencies are failures.

This means that business review candidates should be visible in marts, while broken transformation logic should fail dbt tests.

---

## 16. Mart Modeling Assumptions

The mart layer is business-facing and denormalized.

The primary marts are:

| Mart | Purpose |
|---|---|
| `access_requests_monthly` | Summarizes monthly request inflow, approval/rejection decision flow, and month-end backlog |
| `tool_adoption_monthly` | Compares approved-access stock, monthly usage flow, and monthly spend flow |
| `adoption_review_candidates_monthly` | Classifies approval, usage, and spend alignment states into review candidates |
| `governance_exceptions_current` | Compares current approved access against recent 30-day usage at user-tool grain |

The marts are intended to support review and analysis. They are not audit-grade reconstructions of historical organizational state.

In particular, `adoption_review_candidates_monthly` should be interpreted as a
reviewer-facing follow-up surface, not as a definitive root-cause diagnosis
layer.

### 16.1 Mart grain and metric interpretation

The mart layer intentionally exposes multiple analytical surfaces at different grains to support different business questions.

`tool_adoption_monthly` is designed for monthly team-tool analysis. Its grain is one row per reporting month, team, and tool. Metrics such as `approved_users_total` and `active_users_total` should therefore be interpreted within that row grain.

For example, summing `approved_users_total` across the latest reporting month produces the total of approved-user counts across latest month team-tool rows. It should not be interpreted as a global distinct user count, because the same user may be approved for more than one tool and can therefore contribute to multiple team-tool rows.

This is a deliberate modeling trade-off. The mart is optimized for adoption, usage, and spend alignment by team and tool, not for global user-level deduplication.

When user-level interpretation is required, the warehouse should expose or extend a user-level mart rather than asking the report script to read lower-level models directly. For example:

- `governance_exceptions_current` already provides a current user-tool surface for approval and recent-usage exception review.
- A future `user_tool_adoption_monthly` mart could provide one row per reporting month, user, and tool for monthly user-level adoption analysis.
- A future `user_adoption_monthly` mart could provide one row per reporting month and user for user-level tool portfolio analysis.

This keeps the report layer as a consumer of business-facing marts and keeps grain-specific business semantics inside dbt models.

---

## 17. Stock and Flow Metric Assumptions

The project intentionally combines stock and flow metrics in some marts.

### Flow metrics

Flow metrics describe activity during a reporting period.

Examples:

- `requests_total`
- `approvals_total`
- `rejections_total`
- `active_users_total`
- `total_sessions`
- `total_prompts`
- `spend_usd`

### Stock metrics

Stock metrics describe state as of a point in time.

Examples:

- `pending_total`
- `approved_users_total`

### Important distinction

`spend_usd` is treated as a monthly flow-like measure because it represents spend
recognized for the reporting month, even though it comes from monthly billing
rows rather than daily activity events.

`pending_total` is a month-end backlog stock metric. It is not the number of pending requests submitted during the reporting month.

`approved_users_total` is a month-end approved-access stock metric. It counts users with approved access as of the reporting month end.

---

## 18. Reporting Spine Assumption

Some marts define a reporting spine before joining metric sources.

A reporting spine is the set of reporting keys that should appear in the mart even when one metric source is absent.

For example, `tool_adoption_monthly` compares approval, usage, and spend. A row may exist because approval or usage exists even if a spend row is absent.

### Implication

After metric sources are joined to the reporting spine:

- absent count metrics may be rendered as `0`
- absent boolean flags may be rendered as `false`
- ratio metrics may remain `NULL` when undefined
- spend fields may remain `NULL` when no billing row exists

In this project, a null spend field in a mart can mean that no billing row joined
to the reporting spine. It should not be automatically interpreted as zero spend.

---

## 19. Time and Date Assumptions

The project uses a fixed generated time window.

The generated dataset covers 12 months of synthetic activity. This makes
month-based comparisons reproducible and prevents recent-window logic from
depending on the date when a reviewer runs the project locally.

General temporal assumptions:

- timestamps are normalized for downstream UTC-based logic
- month fields represent the first calendar day of the month
- recent usage is anchored to the maximum available usage date
- generated data should not depend on the local system clock

### Implication

The project is designed for reproducible local validation. Re-running the project with the same generated inputs should preserve the same analytical interpretation.

---

## 20. Natural Key Assumption

The project uses natural business keys in v0.1.0.

Examples include:

- `tool_code`
- `user_id`
- `request_id`

Surrogate keys are not introduced in v0.1.0.

This is a deliberate simplification because the synthetic domain has stable generated identifiers and a compact scope.

### Implication

If the project later expands to multiple source systems, late-arriving records, or production-like slowly changing dimensions, surrogate key strategy should be revisited.

---

## 21. Relationship Assumption

Foreign key-like relationships are modeled through resolvable natural keys.

Examples:

- request requester → user
- request tool → tool
- usage user → user
- usage tool → tool
- spend tool → tool
- request reviewer → user (when reviewer is present)

In dbt tests, these are validated as relationship checks.

### Important interpretation

A relationship check confirms that a key value can resolve to the referenced model. It does not imply that the tested model was constructed from the referenced model.

For example, a fact model can contain `tool_code` and be tested against `dim_tool.tool_code` so that downstream joins are safe.

---

## 22. Synthetic Data Assumption

The dataset is synthetic and deterministic.

For warehouse modeling purposes, the raw data should be interpreted as a
controlled analytical fixture. It is designed to be stable, inspectable, and
reproducible enough to support dbt modeling, testing, documentation, and report
generation.

Requests, approvals, usage, and spend are intentionally correlated. They are
not treated as fully independent random tables.

### Implication

The dataset is not production data and does not make claims about real
enterprise AI tool usage. It exists to provide a realistic enough input boundary
for the downstream warehouse.

---

## 23. Out-of-Scope Modeling

The following are intentionally outside the scope of v0.1.0:

- production orchestration
- live extraction
- cloud warehouse deployment
- application UI
- real access provisioning
- real audit trails
- slowly changing user dimensions
- access revocation
- feature-level product telemetry
- productivity impact measurement
- incident management
- alerting
- production observability
- audit-grade historical reconstruction

These exclusions are intentional and keep the project focused on a minimal, reviewable dbt warehouse.

---

## 24. Future Modeling Extensions

If the warehouse modeling scope is expanded in the future, potential extensions
may involve additional upstream data or source contract changes. Examples
include:

- historical organization snapshots
- slowly changing dimensions
- access revocation-aware approval stock modeling
- license contract modeling
- richer spend allocation models
- feature-level usage telemetry modeling
- productivity or outcome metric marts
- production-style freshness checks
- orchestration metadata integration
- dashboard or BI layer integration

These extensions are not required for v0.1.0 and do not indicate a current plan
to extend the synthetic generator. They would be natural next-step candidates if
the project expands beyond a minimal portfolio warehouse.

---

## 25. Summary

`access-governance-warehouse` v0.1.0 models a simplified access governance domain with deterministic synthetic data and a layered dbt warehouse.

The key assumptions are:

- users are modeled as current-state only
- access requests are final-state request rows
- each dbt model has an explicit grain
- usage is daily aggregated, not event-level
- spend is monthly team-tool billing data
- approval persists because revocation is not modeled
- recent usage is anchored to the generated dataset, not the system clock
- adoption is an operational proxy based on approval, usage, and spend
- business review signals are analytical outputs, not test failures

These assumptions keep the project minimal, reproducible, and reviewable while still demonstrating credible analytics engineering and warehouse modeling practice.
