from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

type RowCountRange = tuple[int, int]


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    seed: int
    anchor_month: date
    n_months: int
    raw_targets: Mapping[str, int]
    raw_target_ranges: Mapping[str, tuple[int, int]]
    allowed_values: Mapping[str, tuple[str, ...]]
    spec_version: str
    base_entity_config: Mapping[str, int]
    org_config: Mapping[str, Any]
    tool_config: tuple[Mapping[str, Any], ...]
    user_profile_config: Mapping[str, Any]
    user_name_config: Mapping[str, Any]
    user_email_config: Mapping[str, Any]
    request_volume_config: Mapping[str, Any]
    request_submission_config: Mapping[str, Any]
    request_review_config: Mapping[str, Any]
    request_duplicate_policy_config: Mapping[str, Any]
    usage_generation_config: Mapping[str, Any]
    spend_generation_config: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class OrgTeam:
    team_name: str
    department_name: str
    size: int
    team_order: int


@dataclass(frozen=True, slots=True)
class OrgSeed:
    departments: tuple[str, ...]
    teams: tuple[OrgTeam, ...]
    team_order_lookup: Mapping[str, int]
    team_to_department_lookup: Mapping[str, str]
    total_users: int


@dataclass(frozen=True, slots=True)
class ToolRecord:
    tool_code: str
    tool_name: str
    vendor_name: str
    tool_category: str
    deployment_scope: str
    risk_tier: str
    is_active: bool
    homepage_url: str | None
    tool_order: int


@dataclass(frozen=True, slots=True)
class ToolSeed:
    tools: tuple[ToolRecord, ...]
    tool_order_lookup: Mapping[str, int]
    active_tool_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UserSlot:
    team_name: str
    department_name: str
    team_order: int
    within_team_slot_order: int
    global_user_rank: int | None = None
    job_level: str | None = None
    employment_status: str | None = None
    user_id: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    user_name: str | None = None
    user_email: str | None = None


@dataclass(frozen=True, slots=True)
class UserUniverses:
    all_user_ids: tuple[str, ...]
    active_user_ids: tuple[str, ...]
    inactive_user_ids: tuple[str, ...]
    active_requester_user_ids_by_team: Mapping[str, tuple[str, ...]]
    reviewer_eligible_user_ids: tuple[str, ...]
    reviewer_eligible_user_ids_by_team: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class RequestSkeleton:
    request_month: date
    month_index: int
    team_name: str
    department_name: str
    team_order: int
    tool_code: str
    tool_order: int
    within_group_request_index: int
    global_request_rank: int | None = None
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class RawOutputPaths:
    root: Path
    tool_catalog: Path
    user_directory: Path
    access_requests: Path
    usage_events_daily: Path
    tool_spend_monthly: Path

    def named_items(self) -> tuple[tuple[str, Path], ...]:
        return (
            ("raw_tool_catalog", self.tool_catalog),
            ("raw_user_directory", self.user_directory),
            ("raw_access_requests", self.access_requests),
            ("raw_usage_events_daily", self.usage_events_daily),
            ("raw_tool_spend_monthly", self.tool_spend_monthly),
        )


@dataclass(frozen=True, slots=True)
class ValidationArtifactPaths:
    root: Path
    summary_markdown: Path
    summary_json: Path

    def named_items(self) -> tuple[tuple[str, Path], ...]:
        return (
            ("generator_validation_summary_markdown", self.summary_markdown),
            ("generator_validation_summary_json", self.summary_json),
        )


@dataclass(frozen=True, slots=True)
class OutputPaths:
    repo_root: Path
    raw: RawOutputPaths
    validation: ValidationArtifactPaths

    def all_directories(self) -> tuple[Path, ...]:
        return (
            self.raw.root,
            self.validation.root,
        )
