# Looker Studio Dashboard

> 日本語版: [looker-studio-dashboard.ja.md](docs/looker-studio-dashboard.ja.md)

## 1. Naming Note

Google announced in April 2026 that Looker Studio is being reintroduced as Data Studio. See the official Google Cloud Blog announcement: [Data Studio returns as new home for Data Cloud assets](https://cloud.google.com/blog/products/data-analytics/looker-studio-is-data-studio).

This repository uses the term "Looker Studio" throughout the documentation because it remains widely used in job descriptions, skill listings, and existing project artifacts.

## 2. Purpose

This document describes the lightweight Looker Studio dashboard artifacts for `access-governance-warehouse` v0.2.1.

The dashboard connects selected BigQuery mart outputs to a small stakeholder-facing report. It demonstrates that the existing dbt marts can support a business intelligence presentation layer without moving business logic out of dbt.

The dashboard is not intended to be production BI infrastructure. It is a portfolio artifact that complements the local DuckDB path and the BigQuery execution path.

The public repository uses screenshots and documentation as reviewable artifacts. A public Looker Studio report link is not required.

## 3. Audience

The dashboard is designed for:

- hiring reviewers
- analytics engineering reviewers
- BI reviewers
- data engineering reviewers
- non-technical stakeholders who want a high-level view of access governance activity

## 4. BI-Facing Path

The dashboard represents the BI-facing extension of the v0.2.0 BigQuery execution path.

```text
BigQuery marts
  -> embedded Looker Studio data sources
  -> dashboard pages
  -> screenshots and documentation
```

The local DuckDB path remains the primary clone-and-run review path. BigQuery and Looker Studio provide cloud warehouse and BI-facing presentation evidence.

## 5. Data Source Strategy

The dashboard uses embedded Looker Studio data sources connected to BigQuery marts.

Business logic, review classifications, grains, and metric-ready outputs remain owned by dbt. Looker Studio is used for presentation, filtering, charting, and screenshot-based documentation.

The dashboard does not require a public report link. Screenshots and documentation are the repository-facing artifacts.

## 6. Connected BigQuery Marts

The dashboard uses the existing v0.2.0 mart layer. No dashboard-specific dbt mart was added for v0.2.1.

| Looker Studio data source | BigQuery mart | Purpose |
|---|---|---|
| Access requests monthly | `access_governance_dbt.access_requests_monthly` | Request trends, approvals, rejections, backlog, and request distribution |
| Tool adoption monthly | `access_governance_dbt.tool_adoption_monthly` | Adoption, usage volume, spend, and cost alignment |
| Adoption review candidates monthly | `access_governance_dbt.adoption_review_candidates_monthly` | Monthly review candidates and prioritization signals |
| Governance exceptions current | `access_governance_dbt.governance_exceptions_current` | Current user-tool governance exception surface |

## 7. Dashboard Pages

The dashboard has three pages.

| Page | Purpose | Primary sources | Screenshot |
|---|---|---|---|
| Executive Overview | Provide a one-minute summary of access requests, adoption, spend, and governance review signals | `access_requests_monthly`, `tool_adoption_monthly`, `governance_exceptions_current`, `adoption_review_candidates_monthly` | `docs/assets/looker-studio/executive_overview_dashboard.png` |
| Tool Adoption and Usage | Show whether approved AI tool access becomes observable usage and how usage aligns with spend | `tool_adoption_monthly` | `docs/assets/looker-studio/tool_adoption_dashboard.png` |
| Governance Exceptions and Review Signals | Show current exception surfaces and monthly review candidates | `governance_exceptions_current`, `adoption_review_candidates_monthly` | `docs/assets/looker-studio/governance_exceptions_dashboard.png` |

## 8. Page 1: Executive Overview

### 8.1 Purpose

The Executive Overview page provides a compact summary of access governance activity, AI tool usage, spend, and current review signals.

### 8.2 Implemented Visuals

| Visual | Source | Metric or dimension | Purpose |
|---|---|---|---|
| Scorecard | `access_requests_monthly` | `requests_total` | Show total access request volume |
| Scorecard | `access_requests_monthly` | approval rate calculated from `approvals_total` and `rejections_total` | Show the share of reviewed requests that were approved |
| Scorecard | `tool_adoption_monthly` | `total_sessions` | Show usage volume |
| Scorecard | `tool_adoption_monthly` | `spend_usd` | Show spend scale |
| Scorecard | `governance_exceptions_current` | used-without-approval rows | Show current unapproved usage signal |
| Time series | `access_requests_monthly` | `reporting_month`, `requests_total`, `approvals_total`, `rejections_total` | Show monthly request and review trends |
| Bar chart | `access_requests_monthly` | `team_name`, `requests_total` | Show top teams by request volume |
| Table | `adoption_review_candidates_monthly` | `reporting_month`, `team_name`, `tool_name`, `risk_tier`, `review_priority`, `review_owner_hint` | Show high-priority review candidates |

### 8.3 Screenshot

![Executive Overview dashboard](assets/looker-studio/executive_overview_dashboard.png)

## 9. Page 2: Tool Adoption and Usage

### 9.1 Purpose

The Tool Adoption and Usage page shows whether approved AI tool access becomes observable usage and how usage aligns with spend.

### 9.2 Implemented Visuals

| Visual | Source | Metric or dimension | Purpose |
|---|---|---|---|
| Scorecard | `tool_adoption_monthly` | `active_users_total` | Show active user-months across the monthly team-tool mart grain |
| Scorecard | `tool_adoption_monthly` | `approved_users_total` | Show approved users summed across monthly team-tool rows |
| Scorecard | `tool_adoption_monthly` | `total_sessions` | Show total usage sessions |
| Scorecard | `tool_adoption_monthly` | `spend_usd` | Show total spend |
| Time series | `tool_adoption_monthly` | `reporting_month`, `active_users_total` | Show active user-month trend |
| Time series | `tool_adoption_monthly` | `reporting_month`, `total_sessions`, `total_prompts` | Show usage volume trend |
| Bar chart | `tool_adoption_monthly` | `tool_name`, `active_users_total` | Show top tools by active user-months |
| Bar chart | `tool_adoption_monthly` | `team_name`, `active_users_total` | Show top teams by active user-months |
| Table | `tool_adoption_monthly` | `reporting_month`, `team_name`, `tool_name`, `total_sessions`, `active_users_total`, `spend_usd`, `cost_per_active_user` | Compare adoption, usage, spend, and cost per active user |

### 9.3 Grain Warning

`tool_adoption_monthly` is at the following grain:

```text
one row per reporting month, team, and tool
```

Metrics such as `active_users_total` and `approved_users_total` should not be interpreted as global distinct user counts. They are summed across monthly team-tool rows.

### 9.4 Screenshot

![Tool Adoption and Usage dashboard](assets/looker-studio/tool_adoption_dashboard.png)

## 10. Page 3: Governance Exceptions and Review Signals

### 10.1 Purpose

The Governance Exceptions and Review Signals page shows current governance exception surfaces and monthly review candidates.

This page is built around the project principle:

> Business exceptions are outputs. Transformation inconsistencies are failures.

### 10.2 Implemented Visuals

| Visual | Source | Metric or dimension | Purpose |
|---|---|---|---|
| Scorecard | `governance_exceptions_current` | `Used Without Approval Count` | Show current user-tool rows with recent usage and no approved access |
| Scorecard | `governance_exceptions_current` | `Approved But Inactive Count` | Show current user-tool rows with approved access and no recent 30-day usage |
| Bar chart | `governance_exceptions_current` | `team_name`, exception counts | Show team-level exception distribution |
| Bar chart | `governance_exceptions_current` | `tool_name`, exception counts | Show tool-level exception distribution |
| Table | `governance_exceptions_current` | `user_id`, `team_name`, `department_name`, `tool_name`, `risk_tier`, `used_without_approval_flag`, `approved_but_inactive_flag` | Provide inspectable current exception examples without exposing personal names or email addresses |
| Table | `adoption_review_candidates_monthly` | `reporting_month`, `team_name`, `tool_name`, `risk_tier`, `review_status`, `review_priority`, `review_owner_hint`, `active_users_total` | Show high-priority monthly review candidates |

### 10.3 Looker Studio Calculated Fields

The following Looker Studio data-source calculated fields are presentation helpers created from existing dbt mart fields. They do not reimplement business classification logic.

| Calculated field | Source | Formula meaning |
|---|---|---|
| `Used Without Approval Count` | `governance_exceptions_current.used_without_approval_flag` | Convert a boolean exception flag into a 0/1 metric for scorecards and bar charts |
| `Approved But Inactive Count` | `governance_exceptions_current.approved_but_inactive_flag` | Convert a boolean exception flag into a 0/1 metric for scorecards and bar charts |

Example formula pattern:

```text
CASE
  WHEN used_without_approval_flag THEN 1
  ELSE 0
END
```

### 10.4 Privacy-Aware Display Choice

`governance_exceptions_current` includes user-level fields, but the dashboard intentionally avoids displaying `user_name` and `user_email`.

The current exception sample uses `user_id` as a synthetic inspection key and excludes personal names and email addresses. This keeps the screenshot artifact aligned with a privacy-aware dashboard design, even though the dataset is synthetic.

### 10.5 Screenshot

![Governance Exceptions and Review Signals dashboard](assets/looker-studio/governance_exceptions_dashboard.png)

## 11. Metric Definitions

| Metric | Definition |
|---|---|
| Total access requests | Sum of `requests_total` from `access_requests_monthly` |
| Approval rate | `SUM(approvals_total) / (SUM(approvals_total) + SUM(rejections_total))`; displayed as a percent |
| Latest pending requests | Month-end pending request stock from the latest reporting month |
| Active user-months | Sum of `active_users_total` across reporting month, team, and tool rows |
| Approved users summed | Sum of `approved_users_total` across reporting month, team, and tool rows; not a global distinct user count |
| Total sessions | Sum of `total_sessions` from `tool_adoption_monthly` |
| Total prompts | Sum of `total_prompts` from `tool_adoption_monthly` |
| Total spend | Sum of `spend_usd` from `tool_adoption_monthly` |
| Cost per active user | `cost_per_active_user` from `tool_adoption_monthly`; interpreted at the mart grain |
| Used without approval | Current user-tool rows with recent usage and no approved access |
| Approved but inactive | Current user-tool rows with approved access and no recent 30-day usage |
| High-priority review candidates | Rows classified with high review priority in `adoption_review_candidates_monthly` |

## 12. Grain Notes

`access_requests_monthly` is a monthly request summary mart. Request metrics should be interpreted as aggregated request counts at the mart grain.

`tool_adoption_monthly` is at the following grain:

```text
one row per reporting month, team, and tool
```

Because of this grain, metrics such as `approved_users_total` and `active_users_total` should not be described as global distinct user counts. They are summed across monthly team-tool rows.

`governance_exceptions_current` is a current snapshot mart. It is not a monthly time series mart, so date range filtering should not be forced onto this page.

## 13. Filter and Control Design

The dashboard uses simple page-level controls and avoids complex report-level interaction behavior.

| Control | Intended fields | Pages | Notes |
|---|---|---|---|
| Date range control | `reporting_month` | Executive Overview; Tool Adoption and Usage | Used for monthly marts |
| Team filter | `team_name` | Optional future refinement | Useful across request, adoption, and exception views |
| Department filter | `department_name` | Optional future refinement | Useful for stakeholder review |
| Tool filter | `tool_name` or `tool_code` | Optional future refinement | Useful for tool-level analysis |
| Risk tier filter | `risk_tier` | Optional future refinement | Useful for governance-focused views |
| Review priority filter | `review_priority` | Optional future refinement | Useful for candidate review tables |
| Review status filter | `review_status` | Optional future refinement | Useful where the source mart exposes review status |

For v0.2.1, the dashboard prioritizes stable screenshot artifacts over complex interactivity. Chart interactions such as cross-filtering, viewer-driven sorting, and zoom are not required for the public artifacts.

## 14. Mart-to-Dashboard Mapping

| Dashboard question | Mart | Example fields |
|---|---|---|
| How many access requests were submitted? | `access_requests_monthly` | `reporting_month`, `requests_total`, `team_name`, `tool_name` |
| What share of reviewed requests were approved? | `access_requests_monthly` | `approvals_total`, `rejections_total` |
| How much AI tool usage is observable? | `tool_adoption_monthly` | `active_users_total`, `total_sessions`, `total_prompts` |
| Which tools or teams show the most adoption? | `tool_adoption_monthly` | `tool_name`, `team_name`, `active_users_total` |
| How does usage align with spend? | `tool_adoption_monthly` | `spend_usd`, `cost_per_active_user`, `active_users_total` |
| Which current user-tool rows need governance review? | `governance_exceptions_current` | `user_id`, `team_name`, `tool_name`, `risk_tier`, `used_without_approval_flag`, `approved_but_inactive_flag` |
| Which monthly adoption rows should be reviewed first? | `adoption_review_candidates_monthly` | `review_priority`, `review_status`, `risk_tier`, `review_owner_hint` |

## 15. Screenshots

Screenshots are the public dashboard artifacts for this repository.

| Page | Screenshot path |
|---|---|
| Executive Overview | `docs/assets/looker-studio/executive_overview_dashboard.png` |
| Tool Adoption and Usage | `docs/assets/looker-studio/tool_adoption_dashboard.png` |
| Governance Exceptions and Review Signals | `docs/assets/looker-studio/governance_exceptions_dashboard.png` |

The screenshots represent the current deterministic v0.2.1 BigQuery mart state.

## 16. Screenshot Masking Policy

Screenshots should not expose:

```text
- Google Cloud project ID
- user email address
- service account email
- private dashboard URL
- billing-related identifiers
- account-specific identifiers
```

The following names may remain visible because they support architectural clarity:

```text
- access_governance_raw
- access_governance_dbt
- access_requests_monthly
- tool_adoption_monthly
- adoption_review_candidates_monthly
- governance_exceptions_current
- synthetic tool names
- synthetic team names
- synthetic metric values
```

## 17. Sharing Policy

The public repository uses screenshots and documentation as the reviewable dashboard artifacts.

## 18. Limitations

This dashboard is intentionally lightweight.

The following items are out of scope for v0.2.1:

```text
- production BI deployment
- dashboard-as-code
- LookML project setup
- Terraform-managed BI infrastructure
- scheduled dashboard delivery
- production access control design
- viewer-specific BigQuery access configuration
- complex dashboard theming
- public dashboard link requirement
```

Additional interpretation limits:

```text
- The dashboard uses deterministic synthetic data, not real operational data.
- `tool_adoption_monthly` metrics are aggregated at reporting month, team, and tool grain.
- `active_users_total` and `approved_users_total` are not global distinct user counts.
- `governance_exceptions_current` is a current snapshot mart, not a monthly time series mart.
- Looker Studio is used for presentation. dbt remains the owner of warehouse transformation logic and business classification logic.
```

## 19. Reproduction Notes

The dashboard depends on the BigQuery execution path introduced in v0.2.0.

Expected source path:

```text
deterministic Parquet fixtures
  -> BigQuery raw tables
  -> dbt BigQuery target
  -> BigQuery marts
  -> embedded Looker Studio data sources
  -> dashboard pages
  -> screenshots and documentation
```

The local DuckDB path remains the primary clone-and-run review path.

To reproduce the dashboard data source state:

1. Load the deterministic raw Parquet fixtures into BigQuery.
2. Run the dbt BigQuery target.
3. Confirm the selected marts exist in `access_governance_dbt`.
4. Connect Looker Studio embedded data sources to the selected BigQuery marts.
5. Recreate or review the three dashboard pages.
6. Compare the recreated dashboard with the committed screenshots under `docs/assets/looker-studio/`.

The dashboard does not require a public Looker Studio link. The repository-facing artifacts are this document and the committed screenshots.

## 20. Dashboard Principle

Business exceptions are outputs. Transformation inconsistencies are failures.
