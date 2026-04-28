from __future__ import annotations

import re
from collections import Counter
from collections.abc import Collection, Hashable, Iterable, Mapping, Sequence
from datetime import date, datetime
from typing import SupportsInt, cast

import pandas as pd

from generator.helpers.dates import UTC, is_timestamp_in_month
from generator.helpers.rounding import finalize_spend_total, quantize_usd
from generator.types import OrgSeed, RuntimeConfig, ToolSeed, UserUniverses


class ValidationError(ValueError):
    """Raised when a low-level generator invariant is violated."""


def assert_allowed_value(
    value: object,
    allowed_values: Collection[object],
    *,
    field_name: str,
) -> None:
    if value not in allowed_values:
        raise ValidationError(
            f"{field_name} must be one of {sorted(map(str, allowed_values))}; got {value!r}."
        )


def assert_allowed_values(
    values: Iterable[object],
    allowed_values: Collection[object],
    *,
    field_name: str,
    allow_null: bool = False,
) -> None:
    invalid_values: set[str] = set()

    for value in values:
        if value is None and allow_null:
            continue
        if value not in allowed_values:
            invalid_values.add(repr(value))

    if invalid_values:
        raise ValidationError(
            f"{field_name} contains invalid values: {sorted(invalid_values)}"
        )


def assert_non_null_fields(
    record: Mapping[str, object],
    *,
    required_fields: Sequence[str],
) -> None:
    missing_fields = [field for field in required_fields if record.get(field) is None]
    if missing_fields:
        raise ValidationError(f"required non-null fields are missing: {missing_fields}")


def assert_unique(
    values: Iterable[Hashable],
    *,
    field_name: str,
) -> None:
    seen: set[Hashable] = set()
    duplicates: set[Hashable] = set()

    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    if duplicates:
        raise ValidationError(
            f"{field_name} must be unique; duplicate values found: {sorted(map(str, duplicates))}"
        )


def assert_references_exist(
    child_values: Iterable[Hashable],
    parent_values: Collection[Hashable],
    *,
    child_field_name: str,
    parent_field_name: str,
) -> None:
    parent_set = set(parent_values)
    missing_values = sorted(
        {str(value) for value in child_values if value not in parent_set}
    )

    if missing_values:
        raise ValidationError(
            f"{child_field_name} contains values not present in {parent_field_name}: "
            f"{missing_values}"
        )


def assert_columns_present(
    df: pd.DataFrame,
    *,
    required_columns: Sequence[str],
    df_name: str = "DataFrame",
) -> None:
    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]
    if missing_columns:
        raise ValidationError(
            f"{df_name} is missing required columns: {missing_columns}"
        )


def _require_str(
    value: object,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name} must be str at validation time; got {type(value)!r}."
        )
    return value


def _require_int(
    value: object,
    *,
    field_name: str,
) -> int:
    if isinstance(value, bool):
        raise ValidationError(
            f"{field_name} must be int-like, not bool; got {value!r}."
        )

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise ValidationError(
                f"{field_name} must be int-like at validation time; got {value!r}."
            ) from exc

    if isinstance(value, float):
        try:
            return int(value)
        except ValueError as exc:
            raise ValidationError(
                f"{field_name} must be int-like at validation time; got {value!r}."
            ) from exc

    if hasattr(value, "__int__"):
        try:
            return int(cast(SupportsInt, value))
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"{field_name} must be int-like at validation time; got {value!r}."
            ) from exc

    raise ValidationError(
        f"{field_name} must be int-like at validation time; got {value!r}."
    )


def _require_date(
    value: object,
    *,
    field_name: str,
) -> date:
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValidationError(
        f"{field_name} must be date-like at validation time; got {type(value)!r}."
    )


def _require_datetime(
    value: object,
    *,
    field_name: str,
) -> datetime:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    raise ValidationError(
        f"{field_name} must be datetime-like at validation time; got {type(value)!r}."
    )


def _require_utc_datetime(
    value: object,
    *,
    field_name: str,
) -> datetime:
    datetime_value = _require_datetime(value, field_name=field_name)
    if datetime_value.tzinfo is None or datetime_value.utcoffset() != UTC.utcoffset(
        None
    ):
        raise ValidationError(
            f"{field_name} must be timezone-aware UTC; got {datetime_value!r}."
        )
    return datetime_value


def _month_sequence(anchor_month: date, n_months: int) -> tuple[date, ...]:
    if n_months < 1:
        raise ValidationError("n_months must be >= 1.")

    anchor_total_month = anchor_month.year * 12 + (anchor_month.month - 1)
    start_total_month = anchor_total_month - (n_months - 1)

    months: list[date] = []
    for offset in range(n_months):
        total_month = start_total_month + offset
        year = total_month // 12
        month = (total_month % 12) + 1
        months.append(date(year, month, 1))

    return tuple(months)


def validate_fixed_seeds(org_seed: OrgSeed, tool_seed: ToolSeed) -> None:
    if not org_seed.departments:
        raise ValidationError("Org seed must contain at least one department.")
    if not org_seed.teams:
        raise ValidationError("Org seed must contain at least one team.")
    if not tool_seed.tools:
        raise ValidationError("Tool seed must contain at least one tool.")

    if len(org_seed.team_order_lookup) != len(org_seed.teams):
        raise ValidationError("team_order_lookup length must match org team count.")

    if len(org_seed.team_to_department_lookup) != len(org_seed.teams):
        raise ValidationError(
            "team_to_department_lookup length must match org team count."
        )

    expected_team_order = tuple(team.team_name for team in org_seed.teams)
    actual_team_order = tuple(org_seed.team_order_lookup.keys())
    if actual_team_order != expected_team_order:
        raise ValidationError(
            "team_order_lookup must preserve the configured team seed order."
        )

    for team in org_seed.teams:
        mapped_department = org_seed.team_to_department_lookup.get(team.team_name)
        if mapped_department != team.department_name:
            raise ValidationError(
                f"Department lookup mismatch for team {team.team_name!r}."
            )

    if len(tool_seed.tool_order_lookup) != len(tool_seed.tools):
        raise ValidationError("tool_order_lookup length must match tool count.")

    expected_tool_order = tuple(tool.tool_code for tool in tool_seed.tools)
    actual_tool_order = tuple(tool_seed.tool_order_lookup.keys())
    if actual_tool_order != expected_tool_order:
        raise ValidationError(
            "tool_order_lookup must preserve the configured tool seed order."
        )

    unknown_active_codes = set(tool_seed.active_tool_codes) - set(expected_tool_order)
    if unknown_active_codes:
        raise ValidationError(
            f"active_tool_codes contains unknown tool codes: {sorted(unknown_active_codes)}"
        )


def validate_user_directory(
    user_df: pd.DataFrame,
    universes: UserUniverses,
    org_seed: OrgSeed,
    config: RuntimeConfig,
) -> None:
    required_columns = (
        "user_id",
        "user_name",
        "user_email",
        "team_name",
        "department_name",
        "job_level",
        "employment_status",
    )
    assert_columns_present(
        user_df,
        required_columns=required_columns,
        df_name="raw_user_directory",
    )

    actual_column_order = tuple(user_df.columns)
    if actual_column_order != required_columns:
        raise ValidationError(
            "raw_user_directory column order must match the canonical raw schema order."
        )

    expected_row_count = config.raw_targets["raw_user_directory_rows"]
    if len(user_df) != expected_row_count:
        raise ValidationError(
            "raw_user_directory row count mismatch; "
            f"expected {expected_row_count}, got {len(user_df)}."
        )

    if user_df.isnull().any().any():
        null_columns = [
            column for column, has_null in user_df.isnull().any().items() if has_null
        ]
        raise ValidationError(
            f"raw_user_directory must not contain nulls; null columns: {null_columns}"
        )

    assert_unique(user_df["user_id"].tolist(), field_name="raw_user_directory.user_id")
    assert_unique(
        user_df["user_name"].tolist(),
        field_name="raw_user_directory.user_name",
    )
    assert_unique(
        user_df["user_email"].tolist(),
        field_name="raw_user_directory.user_email",
    )

    assert_allowed_values(
        user_df["job_level"].tolist(),
        config.allowed_values["job_level"],
        field_name="raw_user_directory.job_level",
    )
    assert_allowed_values(
        user_df["employment_status"].tolist(),
        config.allowed_values["employment_status"],
        field_name="raw_user_directory.employment_status",
    )

    configured_team_names = tuple(team.team_name for team in org_seed.teams)
    configured_departments = set(org_seed.departments)

    assert_allowed_values(
        user_df["team_name"].tolist(),
        configured_team_names,
        field_name="raw_user_directory.team_name",
    )
    assert_allowed_values(
        user_df["department_name"].tolist(),
        configured_departments,
        field_name="raw_user_directory.department_name",
    )

    for row in user_df.itertuples(index=False):
        team_name = _require_str(
            row.team_name, field_name="raw_user_directory.team_name"
        )
        department_name = _require_str(
            row.department_name,
            field_name="raw_user_directory.department_name",
        )
        expected_department = org_seed.team_to_department_lookup[team_name]
        if department_name != expected_department:
            raise ValidationError(
                "department_name must match the fixed team lookup; "
                f"team={team_name!r}, "
                f"expected={expected_department!r}, "
                f"got={department_name!r}."
            )

    expected_team_sequence: list[str] = []
    for team in org_seed.teams:
        expected_team_sequence.extend([team.team_name] * team.size)

    actual_team_sequence = user_df["team_name"].tolist()
    if actual_team_sequence != expected_team_sequence:
        raise ValidationError(
            "raw_user_directory row order must follow canonical team seed order "
            "with contiguous team blocks."
        )

    expected_user_ids = [f"usr_{index:04d}" for index in range(1, len(user_df) + 1)]
    actual_user_ids = user_df["user_id"].tolist()

    if actual_user_ids != expected_user_ids:
        raise ValidationError(
            "user_id sequence must be gap-free and aligned with canonical row order."
        )

    user_id_pattern = re.compile(r"^usr_[0-9]{4}$")
    invalid_user_ids = [
        user_id for user_id in actual_user_ids if not user_id_pattern.fullmatch(user_id)
    ]
    if invalid_user_ids:
        raise ValidationError(
            f"user_id values must match ^usr_[0-9]{{4}}$; invalid values: {invalid_user_ids}"
        )

    for raw_user_name in user_df["user_name"].tolist():
        user_name = _require_str(
            raw_user_name, field_name="raw_user_directory.user_name"
        )
        if user_name != user_name.strip():
            raise ValidationError("user_name must not contain leading/trailing spaces.")
        if "  " in user_name:
            raise ValidationError(
                "user_name must not contain duplicate internal spaces."
            )
        if user_name.count(" ") != 1:
            raise ValidationError("user_name must contain exactly one space separator.")
        if not user_name:
            raise ValidationError("user_name must not be empty.")

    email_domain = str(config.user_email_config["domain"]).strip().lower()
    email_pattern = re.compile(
        rf"^[a-z]+(?:\.[a-z]+)*\.[0-9]{{4}}@{re.escape(email_domain)}$"
    )

    for row in user_df.itertuples(index=False):
        user_email = _require_str(
            row.user_email,
            field_name="raw_user_directory.user_email",
        )
        user_name = _require_str(
            row.user_name,
            field_name="raw_user_directory.user_name",
        )
        user_id = _require_str(
            row.user_id,
            field_name="raw_user_directory.user_id",
        )

        if user_email != user_email.strip():
            raise ValidationError(
                "user_email must not contain leading/trailing spaces."
            )
        if user_email != user_email.lower():
            raise ValidationError("user_email must already be lowercase.")
        if " " in user_email:
            raise ValidationError("user_email must not contain whitespace.")
        if ".." in user_email:
            raise ValidationError("user_email must not contain consecutive dots.")
        if user_email.count("@") != 1:
            raise ValidationError("user_email must contain exactly one '@'.")

        if not email_pattern.fullmatch(user_email):
            raise ValidationError(
                "user_email does not match the required structural pattern; "
                f"got {user_email!r}."
            )

        given_name, family_name = user_name.split(" ", maxsplit=1)
        rank_suffix = user_id.removeprefix("usr_")
        expected_email = (
            f"{given_name.lower()}.{family_name.lower()}.{rank_suffix}@{email_domain}"
        )
        if user_email != expected_email:
            raise ValidationError(
                "user_email must be derived deterministically from user_name and "
                f"user_id; expected {expected_email!r}, got {user_email!r}."
            )

    expected_team_counts = {team.team_name: team.size for team in org_seed.teams}
    actual_team_counts = Counter(user_df["team_name"].tolist())
    if dict(actual_team_counts) != expected_team_counts:
        raise ValidationError(
            "Team counts in raw_user_directory do not match ORG_CONFIG exactly."
        )

    expected_job_level_counts_by_team = config.user_profile_config["job_level"][
        "job_level_counts_by_team"
    ]
    actual_job_level_counts_by_team = (
        user_df.groupby(["team_name", "job_level"], sort=False).size().to_dict()
    )

    for team_name, level_counts in expected_job_level_counts_by_team.items():
        for job_level, expected_count in level_counts.items():
            actual_count = actual_job_level_counts_by_team.get(
                (team_name, job_level), 0
            )
            if actual_count != expected_count:
                raise ValidationError(
                    "Job-level quotas do not match exactly; "
                    f"team={team_name!r}, job_level={job_level!r}, "
                    f"expected={expected_count}, got={actual_count}."
                )

    expected_status_counts = config.user_profile_config["employment_status"][
        "employment_status_counts_by_team_and_job_level"
    ]
    actual_status_counts = (
        user_df.groupby(
            ["team_name", "job_level", "employment_status"],
            sort=False,
        )
        .size()
        .to_dict()
    )

    for team_name, level_map in expected_status_counts.items():
        for job_level, status_map in level_map.items():
            for employment_status, expected_count in status_map.items():
                actual_count = actual_status_counts.get(
                    (team_name, job_level, employment_status),
                    0,
                )
                if actual_count != expected_count:
                    raise ValidationError(
                        "Employment-status quotas do not match exactly; "
                        f"team={team_name!r}, "
                        f"job_level={job_level!r}, "
                        f"employment_status={employment_status!r}, "
                        f"expected={expected_count}, got={actual_count}."
                    )

    inactive_df = user_df.loc[user_df["employment_status"] == "inactive"].copy()
    if (
        not inactive_df.empty
        and not (inactive_df["job_level"] == "individual_contributor").all()
    ):
        raise ValidationError(
            "Inactive users must be individual_contributor only in v0.1.0."
        )

    expected_all_user_ids = tuple(user_df["user_id"].tolist())
    expected_active_user_ids = tuple(
        user_df.loc[user_df["employment_status"] == "active", "user_id"].tolist()
    )
    expected_inactive_user_ids = tuple(
        user_df.loc[user_df["employment_status"] == "inactive", "user_id"].tolist()
    )

    if universes.all_user_ids != expected_all_user_ids:
        raise ValidationError(
            "all_user_ids universe must preserve canonical row order."
        )

    if universes.active_user_ids != expected_active_user_ids:
        raise ValidationError(
            "active_user_ids universe must match active users exactly."
        )

    if universes.inactive_user_ids != expected_inactive_user_ids:
        raise ValidationError(
            "inactive_user_ids universe must match inactive users exactly."
        )

    if set(universes.active_user_ids) & set(universes.inactive_user_ids):
        raise ValidationError("active and inactive user universes must be disjoint.")

    expected_active_requester_by_team: dict[str, tuple[str, ...]] = {}
    for team_name in configured_team_names:
        expected_active_requester_by_team[team_name] = tuple(
            user_df.loc[
                (user_df["team_name"] == team_name)
                & (user_df["employment_status"] == "active"),
                "user_id",
            ].tolist()
        )

    if (
        tuple(universes.active_requester_user_ids_by_team.keys())
        != configured_team_names
    ):
        raise ValidationError(
            "active_requester_user_ids_by_team must preserve configured team order."
        )

    for team_name, expected_ids in expected_active_requester_by_team.items():
        actual_ids = universes.active_requester_user_ids_by_team.get(team_name)
        if actual_ids != expected_ids:
            raise ValidationError(
                "active requester universe mismatch for team "
                f"{team_name!r}: expected {expected_ids}, got {actual_ids}."
            )

    if universes.reviewer_eligible_user_ids != expected_active_user_ids:
        raise ValidationError(
            "reviewer_eligible_user_ids must equal the active-user universe in here."
        )

    if (
        tuple(universes.reviewer_eligible_user_ids_by_team.keys())
        != configured_team_names
    ):
        raise ValidationError(
            "reviewer_eligible_user_ids_by_team must preserve configured team order."
        )

    for team_name, expected_ids in expected_active_requester_by_team.items():
        actual_ids = universes.reviewer_eligible_user_ids_by_team.get(team_name)
        if actual_ids != expected_ids:
            raise ValidationError(
                "reviewer eligible universe mismatch for team "
                f"{team_name!r}: expected {expected_ids}, got {actual_ids}."
            )


def validate_request_volume(
    team_month_df: pd.DataFrame,
    team_month_tool_df: pd.DataFrame,
    org_seed: OrgSeed,
    config: RuntimeConfig,
) -> None:
    required_team_month_columns = (
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "team_order",
        "request_count",
    )
    required_team_month_tool_columns = (
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "team_order",
        "tool_code",
        "tool_order",
        "request_count",
    )

    assert_columns_present(
        team_month_df,
        required_columns=required_team_month_columns,
        df_name="team_month_df",
    )
    assert_columns_present(
        team_month_tool_df,
        required_columns=required_team_month_tool_columns,
        df_name="team_month_tool_df",
    )

    if tuple(team_month_df.columns) != required_team_month_columns:
        raise ValidationError(
            "team_month_df column order must match the canonical  order."
        )

    if tuple(team_month_tool_df.columns) != required_team_month_tool_columns:
        raise ValidationError(
            "team_month_tool_df column order must match the canonical  order."
        )

    if team_month_df.isnull().any().any():
        raise ValidationError("team_month_df must not contain nulls.")

    if team_month_tool_df.isnull().any().any():
        raise ValidationError("team_month_tool_df must not contain nulls.")

    if (team_month_df["request_count"] < 0).any():
        raise ValidationError("team_month_df.request_count must be non-negative.")

    if (team_month_tool_df["request_count"] < 0).any():
        raise ValidationError("team_month_tool_df.request_count must be non-negative.")

    expected_months = _month_sequence(config.anchor_month, config.n_months)
    configured_tool_codes = tuple(str(tool["tool_code"]) for tool in config.tool_config)

    expected_team_month_keys = [
        (
            request_month,
            month_index,
            team.team_name,
            team.department_name,
            team.team_order,
        )
        for month_index, request_month in enumerate(expected_months, start=1)
        for team in org_seed.teams
    ]
    actual_team_month_keys = list(
        team_month_df[
            [
                "request_month",
                "month_index",
                "team_name",
                "department_name",
                "team_order",
            ]
        ].itertuples(index=False, name=None)
    )

    if actual_team_month_keys != expected_team_month_keys:
        raise ValidationError(
            "team_month_df row order must follow month order then configured team order."
        )

    expected_team_month_tool_keys = [
        (
            request_month,
            month_index,
            team.team_name,
            team.department_name,
            team.team_order,
            tool_code,
            tool_order,
        )
        for month_index, request_month in enumerate(expected_months, start=1)
        for team in org_seed.teams
        for tool_order, tool_code in enumerate(configured_tool_codes, start=1)
    ]
    actual_team_month_tool_keys = list(
        team_month_tool_df[
            [
                "request_month",
                "month_index",
                "team_name",
                "department_name",
                "team_order",
                "tool_code",
                "tool_order",
            ]
        ].itertuples(index=False, name=None)
    )

    if actual_team_month_tool_keys != expected_team_month_tool_keys:
        raise ValidationError(
            "team_month_tool_df row order must follow month order, team order, and tool order."
        )

    expected_team_month_rows = config.n_months * len(org_seed.teams)
    if len(team_month_df) != expected_team_month_rows:
        raise ValidationError(
            "team_month_df row count mismatch; "
            f"expected {expected_team_month_rows}, got {len(team_month_df)}."
        )

    expected_team_month_tool_rows = (
        config.n_months * len(org_seed.teams) * len(configured_tool_codes)
    )
    if len(team_month_tool_df) != expected_team_month_tool_rows:
        raise ValidationError(
            "team_month_tool_df row count mismatch; "
            f"expected {expected_team_month_tool_rows}, got {len(team_month_tool_df)}."
        )

    annual_team_targets = config.request_volume_config["annual_team_targets"]
    actual_team_totals = (
        team_month_df.groupby("team_name", sort=False)["request_count"].sum().to_dict()
    )
    expected_team_totals = {
        team_name: int(total) for team_name, total in annual_team_targets.items()
    }
    if actual_team_totals != expected_team_totals:
        raise ValidationError(
            "team_month_df annual team totals must match annual_team_targets exactly."
        )

    expected_total_requests = int(config.raw_targets["raw_access_requests_rows"])
    actual_total_requests = int(team_month_df["request_count"].sum())
    if actual_total_requests != expected_total_requests:
        raise ValidationError(
            "team_month_df total request count mismatch; "
            f"expected {expected_total_requests}, got {actual_total_requests}."
        )

    actual_total_requests_tool = int(team_month_tool_df["request_count"].sum())
    if actual_total_requests_tool != expected_total_requests:
        raise ValidationError(
            "team_month_tool_df total request count mismatch; "
            f"expected {expected_total_requests}, got {actual_total_requests_tool}."
        )

    month_team_totals_from_tools = (
        team_month_tool_df.groupby(
            [
                "request_month",
                "month_index",
                "team_name",
                "department_name",
                "team_order",
            ],
            sort=False,
        )["request_count"]
        .sum()
        .to_dict()
    )

    for row in team_month_df.itertuples(index=False):
        request_month = _require_date(
            row.request_month,
            field_name="team_month_df.request_month",
        )
        month_index = _require_int(
            row.month_index,
            field_name="team_month_df.month_index",
        )
        team_name = _require_str(
            row.team_name,
            field_name="team_month_df.team_name",
        )
        department_name = _require_str(
            row.department_name,
            field_name="team_month_df.department_name",
        )
        team_order = _require_int(
            row.team_order,
            field_name="team_month_df.team_order",
        )
        request_count = _require_int(
            row.request_count,
            field_name="team_month_df.request_count",
        )

        key = (
            request_month,
            month_index,
            team_name,
            department_name,
            team_order,
        )
        actual_count = int(month_team_totals_from_tools.get(key, -1))
        if actual_count != request_count:
            raise ValidationError(
                "team_month_tool_df must sum back to team_month_df exactly; "
                f"key={key!r}, expected={request_count}, got={actual_count}."
            )


def validate_request_skeletons(
    request_skeleton_df: pd.DataFrame,
    team_month_tool_df: pd.DataFrame,
    config: RuntimeConfig,
) -> None:
    required_columns = (
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    )
    assert_columns_present(
        request_skeleton_df,
        required_columns=required_columns,
        df_name="request_skeleton_df",
    )

    if tuple(request_skeleton_df.columns) != required_columns:
        raise ValidationError(
            "request_skeleton_df column order must match the canonical  order."
        )

    expected_row_count = int(config.raw_targets["raw_access_requests_rows"])
    if len(request_skeleton_df) != expected_row_count:
        raise ValidationError(
            "request_skeleton_df row count mismatch; "
            f"expected {expected_row_count}, got {len(request_skeleton_df)}."
        )

    if request_skeleton_df.isnull().any().any():
        raise ValidationError("request_skeleton_df must not contain nulls.")

    if (request_skeleton_df["within_group_request_index"] < 1).any():
        raise ValidationError(
            "within_group_request_index must be >= 1 for all request skeletons."
        )

    expected_request_ids = [
        f"{config.request_volume_config['request_id_prefix']}"
        f"{index:0{int(config.request_volume_config['request_id_zero_pad'])}d}"
        for index in range(1, expected_row_count + 1)
    ]
    actual_request_ids = request_skeleton_df["request_id"].tolist()

    if actual_request_ids != expected_request_ids:
        raise ValidationError(
            "request_id sequence must be gap-free and aligned with canonical skeleton order."
        )

    assert_unique(
        actual_request_ids,
        field_name="request_skeleton_df.request_id",
    )

    request_id_pattern = re.compile(
        rf"^{re.escape(str(config.request_volume_config['request_id_prefix']))}"
        rf"[0-9]{{{int(config.request_volume_config['request_id_zero_pad'])}}}$"
    )
    invalid_request_ids = [
        request_id
        for request_id in actual_request_ids
        if not request_id_pattern.fullmatch(request_id)
    ]
    if invalid_request_ids:
        raise ValidationError(
            "request_id values do not match the required structural pattern; "
            f"invalid values: {invalid_request_ids}"
        )

    expected_global_ranks = list(range(1, expected_row_count + 1))
    actual_global_ranks = request_skeleton_df["global_request_rank"].tolist()
    if actual_global_ranks != expected_global_ranks:
        raise ValidationError(
            "global_request_rank must be gap-free and aligned with canonical skeleton order."
        )

    expected_sorted_keys = list(
        request_skeleton_df.sort_values(
            by=[
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ],
            kind="stable",
        )[
            [
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ]
        ].itertuples(index=False, name=None)
    )
    actual_sorted_keys = list(
        request_skeleton_df[
            [
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ]
        ].itertuples(index=False, name=None)
    )

    if actual_sorted_keys != expected_sorted_keys:
        raise ValidationError(
            "request_skeleton_df row order must follow canonical skeleton order."
        )

    expected_positive_counts = (
        team_month_tool_df.loc[team_month_tool_df["request_count"] > 0]
        .copy()
        .reset_index(drop=True)
    )

    actual_group_counts = (
        request_skeleton_df.groupby(
            [
                "request_month",
                "month_index",
                "team_name",
                "department_name",
                "team_order",
                "tool_code",
                "tool_order",
            ],
            sort=False,
        )
        .size()
        .to_dict()
    )

    expected_group_counts = {}
    for row in expected_positive_counts.itertuples(index=False):
        request_month = _require_date(
            row.request_month,
            field_name="team_month_tool_df.request_month",
        )
        month_index = _require_int(
            row.month_index,
            field_name="team_month_tool_df.month_index",
        )
        team_name = _require_str(
            row.team_name,
            field_name="team_month_tool_df.team_name",
        )
        department_name = _require_str(
            row.department_name,
            field_name="team_month_tool_df.department_name",
        )
        team_order = _require_int(
            row.team_order,
            field_name="team_month_tool_df.team_order",
        )
        tool_code = _require_str(
            row.tool_code,
            field_name="team_month_tool_df.tool_code",
        )
        tool_order = _require_int(
            row.tool_order,
            field_name="team_month_tool_df.tool_order",
        )
        request_count = _require_int(
            row.request_count,
            field_name="team_month_tool_df.request_count",
        )

        key = (
            request_month,
            month_index,
            team_name,
            department_name,
            team_order,
            tool_code,
            tool_order,
        )
        expected_group_counts[key] = request_count

    if actual_group_counts != expected_group_counts:
        raise ValidationError(
            "request_skeleton_df group counts must match positive team_month_tool counts exactly."
        )

    for _, group_df in request_skeleton_df.groupby(
        ["request_month", "month_index", "team_name", "tool_code"],
        sort=False,
    ):
        expected_indices = list(range(1, len(group_df) + 1))
        actual_indices = group_df["within_group_request_index"].tolist()
        if actual_indices != expected_indices:
            raise ValidationError(
                "within_group_request_index must be contiguous from 1..N inside each "
                "(request_month, month_index, team_name, tool_code) group."
            )


def validate_request_submission_side(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    config: RuntimeConfig,
) -> None:
    required_columns = (
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    )

    assert_columns_present(
        request_df,
        required_columns=required_columns,
        df_name="request_submission_df",
    )

    if tuple(request_df.columns) != required_columns:
        raise ValidationError(
            "request_submission_df column order must match the canonical  order."
        )

    expected_row_count = int(config.raw_targets["raw_access_requests_rows"])
    if len(request_df) != expected_row_count:
        raise ValidationError(
            "request_submission_df row count mismatch; "
            f"expected {expected_row_count}, got {len(request_df)}."
        )

    required_non_null_columns = (
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    )
    if request_df[list(required_non_null_columns)].isnull().any().any():
        null_columns = [
            column
            for column, has_null in request_df[list(required_non_null_columns)]
            .isnull()
            .any()
            .items()
            if has_null
        ]
        raise ValidationError(
            "request rows must not contain nulls in submission-side fields; "
            f"null columns: {null_columns}"
        )

    assert_unique(
        request_df["request_id"].tolist(),
        field_name="request_submission_df.request_id",
    )

    assert_references_exist(
        request_df["requester_user_id"].tolist(),
        set(user_df["user_id"].tolist()),
        child_field_name="request_submission_df.requester_user_id",
        parent_field_name="raw_user_directory.user_id",
    )

    assert_allowed_values(
        request_df["request_purpose"].tolist(),
        config.allowed_values["request_purpose"],
        field_name="request_submission_df.request_purpose",
    )
    assert_allowed_values(
        request_df["data_classification"].tolist(),
        config.allowed_values["data_classification"],
        field_name="request_submission_df.data_classification",
    )

    user_lookup: dict[str, dict[str, str]] = {
        _require_str(row.user_id, field_name="raw_user_directory.user_id"): {
            "team_name": _require_str(
                row.team_name,
                field_name="raw_user_directory.team_name",
            ),
            "department_name": _require_str(
                row.department_name,
                field_name="raw_user_directory.department_name",
            ),
            "employment_status": _require_str(
                row.employment_status,
                field_name="raw_user_directory.employment_status",
            ),
        }
        for row in user_df.itertuples(index=False)
    }

    for row in request_df.itertuples(index=False):
        requester_user_id = _require_str(
            row.requester_user_id,
            field_name="request_submission_df.requester_user_id",
        )
        request_id = _require_str(
            row.request_id,
            field_name="request_submission_df.request_id",
        )
        request_team_name = _require_str(
            row.team_name,
            field_name="request_submission_df.team_name",
        )
        request_department_name = _require_str(
            row.department_name,
            field_name="request_submission_df.department_name",
        )
        business_text = _require_str(
            row.business_justification_text,
            field_name="request_submission_df.business_justification_text",
        )
        requested_at = _require_utc_datetime(
            row.requested_at,
            field_name="request_submission_df.requested_at",
        )
        request_month = _require_date(
            row.request_month,
            field_name="request_submission_df.request_month",
        )

        user_meta = user_lookup[requester_user_id]

        if user_meta["team_name"] != request_team_name:
            raise ValidationError(
                "requester_user_id must resolve to a same-team user; "
                f"request_id={request_id!r}, "
                f"request_team={request_team_name!r}, "
                f"user_team={user_meta['team_name']!r}."
            )

        if user_meta["department_name"] != request_department_name:
            raise ValidationError(
                "department_name must remain consistent with requester current-state lookup; "
                f"request_id={request_id!r}, "
                f"request_department={request_department_name!r}, "
                f"user_department={user_meta['department_name']!r}."
            )

        if user_meta["employment_status"] != "active":
            raise ValidationError(
                "Inactive users must not appear as requesters; "
                f"request_id={request_id!r}, requester_user_id={requester_user_id!r}."
            )

        if business_text != business_text.strip():
            raise ValidationError(
                "business_justification_text must not contain leading/trailing spaces."
            )
        if not business_text:
            raise ValidationError("business_justification_text must not be empty.")

        if not is_timestamp_in_month(requested_at, request_month):
            raise ValidationError(
                "requested_at must fall inside the allocated request_month; "
                f"request_id={request_id!r}, "
                f"request_month={request_month!r}, "
                f"requested_at={requested_at!r}."
            )

    expected_order_keys = list(
        request_df.sort_values(
            by=[
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ],
            kind="stable",
        )[
            [
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ]
        ].itertuples(index=False, name=None)
    )
    actual_order_keys = list(
        request_df[
            [
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ]
        ].itertuples(index=False, name=None)
    )
    if actual_order_keys != expected_order_keys:
        raise ValidationError(
            "request rows must preserve canonical request-skeleton order."
        )


def validate_request_review_state(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> None:
    required_columns = (
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
        "review_month",
        "review_month_index",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    )

    assert_columns_present(
        request_df,
        required_columns=required_columns,
        df_name="request_review_df",
    )

    if tuple(request_df.columns) != required_columns:
        raise ValidationError(
            "request_review_df column order must match the canonical  order."
        )

    expected_row_count = int(config.raw_targets["raw_access_requests_rows"])
    if len(request_df) != expected_row_count:
        raise ValidationError(
            "request_review_df row count mismatch; "
            f"expected {expected_row_count}, got {len(request_df)}."
        )

    required_non_null_columns = (
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    )
    if request_df[list(required_non_null_columns)].isnull().any().any():
        null_columns = [
            column
            for column, has_null in request_df[list(required_non_null_columns)]
            .isnull()
            .any()
            .items()
            if has_null
        ]
        raise ValidationError(
            "request rows must not contain nulls in required review-state fields; "
            f"null columns: {null_columns}"
        )

    assert_unique(
        request_df["request_id"].tolist(),
        field_name="request_review_df.request_id",
    )

    assert_allowed_values(
        request_df["request_status"].tolist(),
        config.allowed_values["request_status"],
        field_name="request_review_df.request_status",
    )

    target_status_counts = config.request_review_config["request_status_targets"]
    actual_status_counts = (
        request_df["request_status"].value_counts(dropna=False).to_dict()
    )

    for status, expected_count in target_status_counts.items():
        actual_count = int(actual_status_counts.get(status, 0))
        if actual_count != int(expected_count):
            raise ValidationError(
                " exact status targets are not satisfied; "
                f"status={status!r}, expected={expected_count}, got={actual_count}."
            )

    pending_mask = request_df["request_status"] == "pending"
    reviewed_mask = ~pending_mask

    if request_df.loc[pending_mask, "review_month"].notna().any():
        raise ValidationError("Pending rows must have null review_month in here.")

    if request_df.loc[pending_mask, "review_month_index"].notna().any():
        raise ValidationError("Pending rows must have null review_month_index in here.")

    if request_df.loc[reviewed_mask, "review_month"].isna().any():
        raise ValidationError("Reviewed rows must have non-null review_month in here.")

    if request_df.loc[reviewed_mask, "review_month_index"].isna().any():
        raise ValidationError(
            "Reviewed rows must have non-null review_month_index in here."
        )

    expected_months = _month_sequence(config.anchor_month, config.n_months)
    review_month_lookup = {
        month_index: expected_months[month_index - 1]
        for month_index in range(1, config.n_months + 1)
    }

    for row in request_df.loc[reviewed_mask].itertuples(index=False):
        request_id = _require_str(
            row.request_id,
            field_name="request_review_df.request_id",
        )
        review_month_index = _require_int(
            row.review_month_index,
            field_name="request_review_df.review_month_index",
        )
        request_month_index = _require_int(
            row.month_index,
            field_name="request_review_df.month_index",
        )
        review_month = _require_date(
            row.review_month,
            field_name="request_review_df.review_month",
        )

        if review_month_index < request_month_index:
            raise ValidationError(
                "review_month_index must be >= request month_index for reviewed rows; "
                f"request_id={request_id!r}."
            )
        if review_month_index > config.n_months:
            raise ValidationError(
                "review_month_index must be within the generated month window; "
                f"request_id={request_id!r}."
            )

        expected_review_month = review_month_lookup[review_month_index]
        if review_month != expected_review_month:
            raise ValidationError(
                "review_month must match review_month_index exactly; "
                f"request_id={request_id!r}, "
                f"expected={expected_review_month!r}, got={review_month!r}."
            )

    backlog_targets = config.request_review_config["pending_backlog"][
        "month_end_open_targets_oldest_to_anchor"
    ]

    for month_index, expected_open in enumerate(backlog_targets, start=1):
        open_mask = (request_df["month_index"] <= month_index) & (
            request_df["review_month_index"].isna()
            | (request_df["review_month_index"] > month_index)
        )
        actual_open = int(open_mask.sum())
        if actual_open != int(expected_open):
            raise ValidationError(
                "Month-end open backlog target mismatch; "
                f"month_index={month_index}, expected={expected_open}, got={actual_open}."
            )

    expected_order_keys = list(
        request_df.sort_values(
            by=[
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ],
            kind="stable",
        )[
            [
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ]
        ].itertuples(index=False, name=None)
    )

    actual_order_keys = list(
        request_df[
            [
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ]
        ].itertuples(index=False, name=None)
    )

    if actual_order_keys != expected_order_keys:
        raise ValidationError(
            "request rows must preserve canonical request-skeleton order."
        )


def validate_request_duplicate_policy(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    config: RuntimeConfig,
) -> None:
    validate_request_review_state(request_df, config)

    assert_references_exist(
        request_df["requester_user_id"].tolist(),
        set(user_df["user_id"].tolist()),
        child_field_name="request_review_df.requester_user_id",
        parent_field_name="raw_user_directory.user_id",
    )

    user_lookup: dict[str, dict[str, str]] = {
        _require_str(row.user_id, field_name="raw_user_directory.user_id"): {
            "team_name": _require_str(
                row.team_name,
                field_name="raw_user_directory.team_name",
            ),
            "department_name": _require_str(
                row.department_name,
                field_name="raw_user_directory.department_name",
            ),
            "employment_status": _require_str(
                row.employment_status,
                field_name="raw_user_directory.employment_status",
            ),
        }
        for row in user_df.itertuples(index=False)
    }

    for row in request_df.itertuples(index=False):
        requester_user_id = _require_str(
            row.requester_user_id,
            field_name="request_review_df.requester_user_id",
        )
        request_id = _require_str(
            row.request_id,
            field_name="request_review_df.request_id",
        )
        request_team_name = _require_str(
            row.team_name,
            field_name="request_review_df.team_name",
        )
        request_department_name = _require_str(
            row.department_name,
            field_name="request_review_df.department_name",
        )

        user_meta = user_lookup[requester_user_id]

        if user_meta["team_name"] != request_team_name:
            raise ValidationError(
                "requester_user_id must resolve to a same-team user after duplicate-policy reconciliation; "
                f"request_id={request_id!r}, "
                f"request_team={request_team_name!r}, "
                f"user_team={user_meta['team_name']!r}."
            )

        if user_meta["department_name"] != request_department_name:
            raise ValidationError(
                "department_name must remain consistent with requester current-state lookup after duplicate-policy reconciliation; "
                f"request_id={request_id!r}, "
                f"request_department={request_department_name!r}, "
                f"user_department={user_meta['department_name']!r}."
            )

        if user_meta["employment_status"] != "active":
            raise ValidationError(
                "Inactive users must not appear as requesters after duplicate-policy reconciliation; "
                f"request_id={request_id!r}, requester_user_id={requester_user_id!r}."
            )

    policy = config.request_duplicate_policy_config
    sort_keys = list(policy["sequence_sort_keys"])
    sorted_df = request_df.sort_values(by=sort_keys, kind="stable").copy()

    for (requester_user_id_raw, tool_code_raw), group_df in sorted_df.groupby(
        ["requester_user_id", "tool_code"],
        sort=False,
    ):
        requester_user_id = _require_str(
            requester_user_id_raw,
            field_name="request_review_df.requester_user_id group key",
        )
        tool_code = _require_str(
            tool_code_raw,
            field_name="request_review_df.tool_code group key",
        )

        row_count = int(len(group_df))
        max_requests = int(policy["max_requests_per_user_tool_pair"])
        if row_count > max_requests:
            raise ValidationError(
                "No user-tool pair may exceed the configured total request cap; "
                f"requester_user_id={requester_user_id!r}, "
                f"tool_code={tool_code!r}, "
                f"max_requests={max_requests}, got={row_count}."
            )

        if bool(policy["same_calendar_month_duplicates_forbidden"]):
            request_month_keys = [
                _require_date(
                    value,
                    field_name="request_review_df.request_month",
                ).isoformat()
                for value in group_df["request_month"].tolist()
            ]
            if len(request_month_keys) != len(set(request_month_keys)):
                raise ValidationError(
                    "Same-calendar-month duplicate requests are forbidden for a user-tool pair; "
                    f"requester_user_id={requester_user_id!r}, tool_code={tool_code!r}."
                )

        statuses = [
            _require_str(
                value,
                field_name="request_review_df.request_status",
            )
            for value in group_df["request_status"].tolist()
        ]
        pending_count = statuses.count("pending")
        max_pending = int(policy["max_pending_requests_per_user_tool_pair"])
        if pending_count > max_pending:
            raise ValidationError(
                "A user-tool pair must not have more than the configured pending count; "
                f"requester_user_id={requester_user_id!r}, "
                f"tool_code={tool_code!r}, "
                f"max_pending={max_pending}, got={pending_count}."
            )

        if row_count > 1 and bool(
            policy["all_non_final_requests_in_multi_request_sequence_must_be_rejected"]
        ):
            non_final_statuses = statuses[:-1]
            if any(status != "rejected" for status in non_final_statuses):
                raise ValidationError(
                    "All non-final requests in a multi-request user-tool sequence must be rejected; "
                    f"requester_user_id={requester_user_id!r}, "
                    f"tool_code={tool_code!r}, "
                    f"statuses={statuses!r}."
                )

        if bool(policy["later_request_after_approved_forbidden"]):
            for earlier_status in statuses[:-1]:
                if earlier_status == "approved":
                    raise ValidationError(
                        "No later request may exist after an approved request for the same user-tool pair; "
                        f"requester_user_id={requester_user_id!r}, "
                        f"tool_code={tool_code!r}, "
                        f"statuses={statuses!r}."
                    )

        if bool(policy["later_request_after_pending_forbidden"]):
            for earlier_status in statuses[:-1]:
                if earlier_status == "pending":
                    raise ValidationError(
                        "No later request may exist after a pending request for the same user-tool pair; "
                        f"requester_user_id={requester_user_id!r}, "
                        f"tool_code={tool_code!r}, "
                        f"statuses={statuses!r}."
                    )


def validate_review_detail_fields(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    config: RuntimeConfig,
) -> None:
    legacy_columns = (
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
        "review_month",
        "review_month_index",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    )
    validate_request_duplicate_policy(
        request_df.loc[:, legacy_columns].copy(),
        user_df,
        config,
    )

    required_columns = (
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
        "review_month",
        "review_month_index",
        "reviewed_at",
        "reviewed_by_user_id",
        "review_comment_text",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    )
    assert_columns_present(
        request_df,
        required_columns=required_columns,
        df_name="request_review_detail_df",
    )

    if tuple(request_df.columns) != required_columns:
        raise ValidationError(
            "request_review_detail_df column order must match the canonical order."
        )

    expected_row_count = int(config.raw_targets["raw_access_requests_rows"])
    if len(request_df) != expected_row_count:
        raise ValidationError(
            "request_review_detail_df row count mismatch; "
            f"expected {expected_row_count}, got {len(request_df)}."
        )

    user_lookup: dict[str, dict[str, str]] = {
        _require_str(row.user_id, field_name="raw_user_directory.user_id"): {
            "team_name": _require_str(
                row.team_name,
                field_name="raw_user_directory.team_name",
            ),
            "department_name": _require_str(
                row.department_name,
                field_name="raw_user_directory.department_name",
            ),
            "employment_status": _require_str(
                row.employment_status,
                field_name="raw_user_directory.employment_status",
            ),
        }
        for row in user_df.itertuples(index=False)
    }

    reviewer_ids = [
        _require_str(
            value,
            field_name="request_review_detail_df.reviewed_by_user_id",
        )
        for value in request_df["reviewed_by_user_id"].tolist()
        if value is not None and not pd.isna(value)
    ]
    assert_references_exist(
        reviewer_ids,
        set(user_df["user_id"].tolist()),
        child_field_name="request_review_detail_df.reviewed_by_user_id",
        parent_field_name="raw_user_directory.user_id",
    )

    pending_mask = request_df["request_status"] == "pending"
    approved_mask = request_df["request_status"] == "approved"
    rejected_mask = request_df["request_status"] == "rejected"
    reviewed_mask = approved_mask | rejected_mask

    if request_df.loc[pending_mask, "reviewed_at"].notna().any():
        raise ValidationError("Pending rows must have null reviewed_at.")

    if request_df.loc[pending_mask, "reviewed_by_user_id"].notna().any():
        raise ValidationError("Pending rows must have null reviewed_by_user_id.")

    if request_df.loc[pending_mask, "review_comment_text"].notna().any():
        raise ValidationError("Pending rows must have null review_comment_text.")

    if request_df.loc[approved_mask, "reviewed_at"].isna().any():
        raise ValidationError("Approved rows must have non-null reviewed_at.")

    if request_df.loc[approved_mask, "reviewed_by_user_id"].isna().any():
        raise ValidationError("Approved rows must have non-null reviewed_by_user_id.")

    if request_df.loc[rejected_mask, "reviewed_at"].isna().any():
        raise ValidationError("Rejected rows must have non-null reviewed_at.")

    if request_df.loc[rejected_mask, "reviewed_by_user_id"].isna().any():
        raise ValidationError("Rejected rows must have non-null reviewed_by_user_id.")

    if request_df.loc[rejected_mask, "review_comment_text"].isna().any():
        raise ValidationError("Rejected rows must have non-null review_comment_text.")

    for row in request_df.loc[reviewed_mask].itertuples(index=False):
        request_id = _require_str(
            row.request_id,
            field_name="request_review_detail_df.request_id",
        )
        reviewed_at = _require_utc_datetime(
            row.reviewed_at,
            field_name="request_review_detail_df.reviewed_at",
        )
        requested_at = _require_utc_datetime(
            row.requested_at,
            field_name="request_review_detail_df.requested_at",
        )
        review_month = _require_date(
            row.review_month,
            field_name="request_review_detail_df.review_month",
        )
        reviewer_user_id = _require_str(
            row.reviewed_by_user_id,
            field_name="request_review_detail_df.reviewed_by_user_id",
        )
        requester_user_id = _require_str(
            row.requester_user_id,
            field_name="request_review_detail_df.requester_user_id",
        )

        if reviewed_at <= requested_at:
            raise ValidationError(
                "reviewed_at must be strictly after requested_at for reviewed rows; "
                f"request_id={request_id!r}."
            )

        if not is_timestamp_in_month(reviewed_at, review_month):
            raise ValidationError(
                "reviewed_at must fall inside assigned review_month; "
                f"request_id={request_id!r}, "
                f"review_month={review_month!r}, "
                f"reviewed_at={reviewed_at!r}."
            )

        reviewer_meta = user_lookup[reviewer_user_id]

        if reviewer_meta["employment_status"] != "active":
            raise ValidationError(
                "Inactive users must not appear as reviewers; "
                f"request_id={request_id!r}, reviewed_by_user_id={reviewer_user_id!r}."
            )

        if reviewer_user_id == requester_user_id:
            raise ValidationError(
                "Self review is forbidden; "
                f"request_id={request_id!r}, user_id={reviewer_user_id!r}."
            )

        if row.review_comment_text is not None and not pd.isna(row.review_comment_text):
            review_comment = _require_str(
                row.review_comment_text,
                field_name="request_review_detail_df.review_comment_text",
            )
            if review_comment != review_comment.strip():
                raise ValidationError(
                    "review_comment_text must not contain leading/trailing spaces."
                )
            if not review_comment:
                raise ValidationError(
                    "review_comment_text must not be empty when present."
                )

    expected_order_keys = list(
        request_df.sort_values(
            by=[
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ],
            kind="stable",
        )[
            [
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ]
        ].itertuples(index=False, name=None)
    )
    actual_order_keys = list(
        request_df[
            [
                "request_month",
                "month_index",
                "team_order",
                "tool_order",
                "within_group_request_index",
                "request_id",
            ]
        ].itertuples(index=False, name=None)
    )
    if actual_order_keys != expected_order_keys:
        raise ValidationError(
            "request rows must preserve canonical request-skeleton order."
        )


def validate_usage_events_daily(
    usage_df: pd.DataFrame,
    user_df: pd.DataFrame,
    approved_active_pairs_df: pd.DataFrame,
    approved_inactive_pairs_df: pd.DataFrame,
    anomaly_pairs_df: pd.DataFrame,
    config: RuntimeConfig,
) -> None:
    required_columns = (
        "usage_date",
        "user_id",
        "tool_code",
        "session_count",
        "prompt_count",
        "input_tokens_total",
        "output_tokens_total",
    )
    assert_columns_present(
        usage_df,
        required_columns=required_columns,
        df_name="raw_usage_events_daily",
    )

    if tuple(usage_df.columns) != required_columns:
        raise ValidationError(
            "raw_usage_events_daily column order must match the canonical raw schema order."
        )

    min_rows, max_rows = config.raw_target_ranges["raw_usage_events_daily_rows"]
    if not (int(min_rows) <= len(usage_df) <= int(max_rows)):
        raise ValidationError(
            "raw_usage_events_daily row count must remain within the configured target range; "
            f"expected_range=({min_rows}, {max_rows}), got={len(usage_df)}."
        )

    if usage_df.isnull().any().any():
        null_columns = [
            column for column, has_null in usage_df.isnull().any().items() if has_null
        ]
        raise ValidationError(
            f"raw_usage_events_daily must not contain nulls; null columns: {null_columns}"
        )

    assert_references_exist(
        usage_df["user_id"].tolist(),
        set(user_df["user_id"].tolist()),
        child_field_name="raw_usage_events_daily.user_id",
        parent_field_name="raw_user_directory.user_id",
    )

    configured_tool_codes = {str(tool["tool_code"]) for tool in config.tool_config}
    assert_references_exist(
        usage_df["tool_code"].tolist(),
        configured_tool_codes,
        child_field_name="raw_usage_events_daily.tool_code",
        parent_field_name="raw_tool_catalog.tool_code",
    )

    composite_keys = list(
        usage_df[["usage_date", "user_id", "tool_code"]].itertuples(
            index=False, name=None
        )
    )
    assert_unique(
        composite_keys,
        field_name="raw_usage_events_daily (usage_date, user_id, tool_code)",
    )

    metric_columns = [
        "session_count",
        "prompt_count",
        "input_tokens_total",
        "output_tokens_total",
    ]
    for column in metric_columns:
        if (usage_df[column] < 0).any():
            raise ValidationError(f"{column} must be non-negative for all usage rows.")

    if (usage_df["session_count"] <= 0).any():
        raise ValidationError("Every emitted usage row must have session_count > 0.")

    if (usage_df["prompt_count"] <= 0).any():
        raise ValidationError("Every emitted usage row must have prompt_count > 0.")

    if (usage_df["input_tokens_total"] <= 0).any():
        raise ValidationError(
            "Every emitted usage row must have input_tokens_total > 0."
        )

    if (usage_df["output_tokens_total"] <= 0).any():
        raise ValidationError(
            "Every emitted usage row must have output_tokens_total > 0."
        )

    invalid_prompt_relation_df = usage_df.loc[
        usage_df["prompt_count"] < usage_df["session_count"]
    ].copy()
    if not invalid_prompt_relation_df.empty:
        raise ValidationError(
            "prompt_count must be >= session_count for all emitted usage rows."
        )

    invalid_input_relation_df = usage_df.loc[
        usage_df["input_tokens_total"] < usage_df["prompt_count"]
    ].copy()
    if not invalid_input_relation_df.empty:
        raise ValidationError(
            "input_tokens_total must be >= prompt_count for all emitted usage rows."
        )

    invalid_output_relation_df = usage_df.loc[
        usage_df["output_tokens_total"] < usage_df["prompt_count"]
    ].copy()
    if not invalid_output_relation_df.empty:
        raise ValidationError(
            "output_tokens_total must be >= prompt_count for all emitted usage rows."
        )

    user_lookup = {
        _require_str(
            row.user_id, field_name="raw_user_directory.user_id"
        ): _require_str(
            row.employment_status,
            field_name="raw_user_directory.employment_status",
        )
        for row in user_df.itertuples(index=False)
    }
    inactive_user_ids = sorted(
        {
            _require_str(row.user_id, field_name="raw_usage_events_daily.user_id")
            for row in usage_df.itertuples(index=False)
            if user_lookup[
                _require_str(row.user_id, field_name="raw_usage_events_daily.user_id")
            ]
            != "active"
        }
    )
    if inactive_user_ids:
        raise ValidationError(
            "Inactive users must not appear in raw_usage_events_daily; "
            f"invalid user_ids={inactive_user_ids}"
        )

    approved_active_pair_lookup = {
        (
            _require_str(row.user_id, field_name="approved_active_pairs.user_id"),
            _require_str(row.tool_code, field_name="approved_active_pairs.tool_code"),
        ): _require_date(
            row.first_approved_at,
            field_name="approved_active_pairs.first_approved_at",
        )
        for row in approved_active_pairs_df.itertuples(index=False)
    }
    approved_inactive_pair_keys = {
        (
            _require_str(row.user_id, field_name="approved_inactive_pairs.user_id"),
            _require_str(row.tool_code, field_name="approved_inactive_pairs.tool_code"),
        )
        for row in approved_inactive_pairs_df.itertuples(index=False)
    }
    anomaly_pair_keys = {
        (
            _require_str(row.user_id, field_name="anomaly_pairs.user_id"),
            _require_str(row.tool_code, field_name="anomaly_pairs.tool_code"),
        )
        for row in anomaly_pairs_df.itertuples(index=False)
    }

    observed_pair_keys = {
        (
            _require_str(row.user_id, field_name="raw_usage_events_daily.user_id"),
            _require_str(row.tool_code, field_name="raw_usage_events_daily.tool_code"),
        )
        for row in usage_df.itertuples(index=False)
    }

    missing_active_pairs = sorted(
        approved_active_pair_lookup.keys() - observed_pair_keys
    )
    if missing_active_pairs:
        raise ValidationError(
            "Every approved-active current pair must produce at least one usage row; "
            f"missing_pairs={missing_active_pairs[:10]!r}"
        )

    unexpected_inactive_pairs = sorted(approved_inactive_pair_keys & observed_pair_keys)
    if unexpected_inactive_pairs:
        raise ValidationError(
            "Approved-but-inactive pairs must not produce usage rows; "
            f"unexpected_pairs={unexpected_inactive_pairs[:10]!r}"
        )

    missing_anomaly_pairs = sorted(anomaly_pair_keys - observed_pair_keys)
    if missing_anomaly_pairs:
        raise ValidationError(
            "Every selected anomaly pair must produce at least one usage row; "
            f"missing_pairs={missing_anomaly_pairs[:10]!r}"
        )

    allowed_pair_keys = set(approved_active_pair_lookup.keys()) | anomaly_pair_keys
    unexpected_pair_keys = sorted(observed_pair_keys - allowed_pair_keys)
    if unexpected_pair_keys:
        raise ValidationError(
            "raw_usage_events_daily contains pair keys that were not selected into the active pair universe; "
            f"unexpected_pairs={unexpected_pair_keys[:10]!r}"
        )

    for row in usage_df.itertuples(index=False):
        user_id = _require_str(
            row.user_id,
            field_name="raw_usage_events_daily.user_id",
        )
        tool_code = _require_str(
            row.tool_code,
            field_name="raw_usage_events_daily.tool_code",
        )
        usage_date = _require_date(
            row.usage_date,
            field_name="raw_usage_events_daily.usage_date",
        )

        key = (user_id, tool_code)
        if key in approved_active_pair_lookup:
            first_approved_date = approved_active_pair_lookup[key]
            if usage_date < first_approved_date:
                raise ValidationError(
                    "Approved normal usage must not precede first approval date; "
                    f"user_id={user_id!r}, tool_code={tool_code!r}, "
                    f"usage_date={usage_date!r}, first_approved_date={first_approved_date!r}."
                )

    expected_order_keys = list(
        usage_df.sort_values(
            by=["usage_date", "user_id", "tool_code"],
            kind="stable",
        )[["usage_date", "user_id", "tool_code"]].itertuples(index=False, name=None)
    )
    actual_order_keys = list(
        usage_df[["usage_date", "user_id", "tool_code"]].itertuples(
            index=False, name=None
        )
    )
    if actual_order_keys != expected_order_keys:
        raise ValidationError(
            "raw_usage_events_daily row order must be sorted by usage_date, user_id, tool_code."
        )


def validate_tool_spend_monthly(
    spend_df: pd.DataFrame,
    org_seed: OrgSeed,
    tool_seed: ToolSeed,
    config: RuntimeConfig,
) -> None:
    required_columns = (
        "billing_month",
        "team_name",
        "department_name",
        "tool_code",
        "licensed_seats",
        "fixed_license_cost_usd",
        "variable_usage_cost_usd",
        "spend_usd",
    )
    assert_columns_present(
        spend_df,
        required_columns=required_columns,
        df_name="raw_tool_spend_monthly",
    )

    if tuple(spend_df.columns) != required_columns:
        raise ValidationError(
            "raw_tool_spend_monthly column order must match the canonical raw schema order."
        )

    exact_target = int(
        config.spend_generation_config["qa_rules"][
            "raw_tool_spend_monthly_rows_exact_target"
        ]
    )
    if len(spend_df) != exact_target:
        raise ValidationError(
            "raw_tool_spend_monthly row count must hit the exact configured target; "
            f"expected={exact_target}, got={len(spend_df)}."
        )

    min_rows, max_rows = config.raw_target_ranges["raw_tool_spend_monthly_rows"]
    if not (int(min_rows) <= len(spend_df) <= int(max_rows)):
        raise ValidationError(
            "raw_tool_spend_monthly row count must remain within the configured target range; "
            f"expected_range=({min_rows}, {max_rows}), got={len(spend_df)}."
        )

    if spend_df.isnull().any().any():
        null_columns = [
            column for column, has_null in spend_df.isnull().any().items() if has_null
        ]
        raise ValidationError(
            "raw_tool_spend_monthly must not contain nulls; "
            f"null columns={null_columns}"
        )

    configured_team_names = tuple(team.team_name for team in org_seed.teams)
    assert_allowed_values(
        spend_df["team_name"].tolist(),
        configured_team_names,
        field_name="raw_tool_spend_monthly.team_name",
    )

    assert_references_exist(
        spend_df["tool_code"].tolist(),
        set(tool_seed.tool_order_lookup.keys()),
        child_field_name="raw_tool_spend_monthly.tool_code",
        parent_field_name="raw_tool_catalog.tool_code",
    )

    composite_keys = list(
        spend_df[["billing_month", "team_name", "tool_code"]].itertuples(
            index=False,
            name=None,
        )
    )
    assert_unique(
        composite_keys,
        field_name="raw_tool_spend_monthly (billing_month, team_name, tool_code)",
    )

    team_size_lookup = {team.team_name: team.size for team in org_seed.teams}
    team_order_lookup = dict(org_seed.team_order_lookup)
    tool_order_lookup = dict(tool_seed.tool_order_lookup)

    min_seats = int(
        config.spend_generation_config["qa_rules"]["licensed_seats_min_if_billed"]
    )
    max_seats = int(
        config.spend_generation_config["qa_rules"]["licensed_seats_max_global"]
    )

    for row in spend_df.itertuples(index=False):
        billing_month = pd.Timestamp(row.billing_month)
        if billing_month.day != 1:
            raise ValidationError(
                "billing_month must always be the first calendar day of a month; "
                f"got={row.billing_month!r}."
            )

        expected_department = org_seed.team_to_department_lookup[str(row.team_name)]
        if str(row.department_name) != expected_department:
            raise ValidationError(
                "department_name must match the fixed lookup for emitted team_name; "
                f"team_name={row.team_name!r}, "
                f"expected_department={expected_department!r}, "
                f"got={row.department_name!r}."
            )

        licensed_seats = int(row.licensed_seats)
        if licensed_seats < 0:
            raise ValidationError("licensed_seats must be non-negative.")
        if licensed_seats < min_seats:
            raise ValidationError(
                "licensed_seats must satisfy the billed-row minimum; "
                f"min={min_seats}, got={licensed_seats}."
            )
        if licensed_seats > max_seats:
            raise ValidationError(
                "licensed_seats must not exceed the configured global max; "
                f"max={max_seats}, got={licensed_seats}."
            )
        if licensed_seats > int(team_size_lookup[str(row.team_name)]):
            raise ValidationError(
                "licensed_seats must not exceed team size; "
                f"team_name={row.team_name!r}, "
                f"team_size={team_size_lookup[str(row.team_name)]}, "
                f"got={licensed_seats}."
            )

        fixed_cost = quantize_usd(row.fixed_license_cost_usd)
        variable_cost = quantize_usd(row.variable_usage_cost_usd)
        spend_total = quantize_usd(row.spend_usd)
        expected_total = finalize_spend_total(fixed_cost, variable_cost)

        if fixed_cost <= quantize_usd(0):
            raise ValidationError(
                "fixed_license_cost_usd must be strictly positive for every emitted billed row."
            )
        if variable_cost < quantize_usd(0):
            raise ValidationError(
                "variable_usage_cost_usd must be non-negative for every emitted billed row."
            )
        if spend_total <= quantize_usd(0):
            raise ValidationError(
                "spend_usd must be strictly positive for every emitted billed row."
            )
        if spend_total != expected_total:
            raise ValidationError(
                "spend_usd must equal fixed_license_cost_usd + variable_usage_cost_usd "
                "on emitted raw values."
            )

    expected_order_df = (
        spend_df.assign(
            _team_order=spend_df["team_name"].map(team_order_lookup),
            _tool_order=spend_df["tool_code"].map(tool_order_lookup),
        )
        .sort_values(
            by=["billing_month", "_team_order", "_tool_order"],
            kind="stable",
        )
        .loc[:, ["billing_month", "team_name", "tool_code"]]
    )
    actual_order_df = spend_df.loc[:, ["billing_month", "team_name", "tool_code"]]

    expected_order_keys = list(expected_order_df.itertuples(index=False, name=None))
    actual_order_keys = list(actual_order_df.itertuples(index=False, name=None))

    if actual_order_keys != expected_order_keys:
        raise ValidationError(
            "raw_tool_spend_monthly row order must be sorted by billing_month, team seed order, tool_code."
        )


def validate_raw_tool_catalog(
    tool_df: pd.DataFrame,
    tool_seed: ToolSeed,
    config: RuntimeConfig,
) -> None:
    required_columns = (
        "tool_code",
        "tool_name",
        "vendor_name",
        "tool_category",
        "deployment_scope",
        "risk_tier",
        "is_active",
        "homepage_url",
    )
    assert_columns_present(
        tool_df,
        required_columns=required_columns,
        df_name="raw_tool_catalog",
    )

    if tuple(tool_df.columns) != required_columns:
        raise ValidationError(
            "raw_tool_catalog column order must match the canonical raw schema order."
        )

    expected_row_count = int(config.raw_targets["raw_tool_catalog_rows"])
    if len(tool_df) != expected_row_count:
        raise ValidationError(
            "raw_tool_catalog row count mismatch; "
            f"expected={expected_row_count}, got={len(tool_df)}."
        )

    non_nullable_columns = (
        "tool_code",
        "tool_name",
        "vendor_name",
        "tool_category",
        "deployment_scope",
        "risk_tier",
        "is_active",
    )
    if tool_df[list(non_nullable_columns)].isnull().any().any():
        null_columns = [
            column
            for column, has_null in tool_df[list(non_nullable_columns)]
            .isnull()
            .any()
            .items()
            if has_null
        ]
        raise ValidationError(
            "raw_tool_catalog must not contain nulls in non-nullable columns; "
            f"null_columns={null_columns}"
        )

    assert_unique(
        tool_df["tool_code"].tolist(),
        field_name="raw_tool_catalog.tool_code",
    )
    assert_allowed_values(
        tool_df["tool_category"].tolist(),
        config.allowed_values["tool_category"],
        field_name="raw_tool_catalog.tool_category",
    )
    assert_allowed_values(
        tool_df["deployment_scope"].tolist(),
        config.allowed_values["deployment_scope"],
        field_name="raw_tool_catalog.deployment_scope",
    )
    assert_allowed_values(
        tool_df["risk_tier"].tolist(),
        config.allowed_values["risk_tier"],
        field_name="raw_tool_catalog.risk_tier",
    )

    expected_records = [
        {
            "tool_code": tool.tool_code,
            "tool_name": tool.tool_name,
            "vendor_name": tool.vendor_name,
            "tool_category": tool.tool_category,
            "deployment_scope": tool.deployment_scope,
            "risk_tier": tool.risk_tier,
            "is_active": tool.is_active,
            "homepage_url": tool.homepage_url,
        }
        for tool in tool_seed.tools
    ]
    actual_records = (
        tool_df.reset_index(drop=True)
        .where(pd.notna(tool_df.reset_index(drop=True)), None)
        .to_dict(orient="records")
    )

    if actual_records != expected_records:
        raise ValidationError(
            "raw_tool_catalog must match the configured tool seed exactly and preserve seed order."
        )


def validate_raw_access_requests(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    tool_seed: ToolSeed,
    config: RuntimeConfig,
) -> None:
    required_columns = (
        "request_id",
        "requested_at",
        "requester_user_id",
        "tool_code",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
        "reviewed_at",
        "reviewed_by_user_id",
        "review_comment_text",
    )
    assert_columns_present(
        request_df,
        required_columns=required_columns,
        df_name="raw_access_requests",
    )

    if tuple(request_df.columns) != required_columns:
        raise ValidationError(
            "raw_access_requests column order must match the canonical raw schema order."
        )

    expected_row_count = int(config.raw_targets["raw_access_requests_rows"])
    if len(request_df) != expected_row_count:
        raise ValidationError(
            "raw_access_requests row count mismatch; "
            f"expected={expected_row_count}, got={len(request_df)}."
        )

    min_rows, max_rows = config.raw_target_ranges["raw_access_requests_rows"]
    if not (int(min_rows) <= len(request_df) <= int(max_rows)):
        raise ValidationError(
            "raw_access_requests row count must remain within the configured target range; "
            f"expected_range=({min_rows}, {max_rows}), got={len(request_df)}."
        )

    required_non_null_columns = (
        "request_id",
        "requested_at",
        "requester_user_id",
        "tool_code",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
    )
    if request_df[list(required_non_null_columns)].isnull().any().any():
        null_columns = [
            column
            for column, has_null in request_df[list(required_non_null_columns)]
            .isnull()
            .any()
            .items()
            if has_null
        ]
        raise ValidationError(
            "raw_access_requests must not contain nulls in non-nullable columns; "
            f"null_columns={null_columns}"
        )

    assert_unique(
        request_df["request_id"].tolist(),
        field_name="raw_access_requests.request_id",
    )

    request_id_pattern = re.compile(
        rf"^{re.escape(str(config.request_volume_config['request_id_prefix']))}"
        rf"[0-9]{{{int(config.request_volume_config['request_id_zero_pad'])}}}$"
    )
    invalid_request_ids = [
        request_id
        for request_id in request_df["request_id"].tolist()
        if not request_id_pattern.fullmatch(str(request_id))
    ]
    if invalid_request_ids:
        raise ValidationError(
            "raw_access_requests.request_id contains invalid structural values; "
            f"invalid={invalid_request_ids}"
        )

    expected_request_ids = {
        f"{config.request_volume_config['request_id_prefix']}"
        f"{index:0{int(config.request_volume_config['request_id_zero_pad'])}d}"
        for index in range(1, expected_row_count + 1)
    }
    actual_request_ids = set(request_df["request_id"].tolist())
    if actual_request_ids != expected_request_ids:
        raise ValidationError(
            "raw_access_requests.request_id must be gap-free as a set over the expected ID domain."
        )

    user_ids = set(user_df["user_id"].tolist())
    tool_codes = set(tool_seed.tool_order_lookup.keys())

    assert_references_exist(
        request_df["requester_user_id"].tolist(),
        user_ids,
        child_field_name="raw_access_requests.requester_user_id",
        parent_field_name="raw_user_directory.user_id",
    )
    assert_references_exist(
        request_df["tool_code"].tolist(),
        tool_codes,
        child_field_name="raw_access_requests.tool_code",
        parent_field_name="raw_tool_catalog.tool_code",
    )

    reviewed_by_values = [
        value
        for value in request_df["reviewed_by_user_id"].tolist()
        if value is not None and not pd.isna(value)
    ]
    assert_references_exist(
        reviewed_by_values,
        user_ids,
        child_field_name="raw_access_requests.reviewed_by_user_id",
        parent_field_name="raw_user_directory.user_id",
    )

    assert_allowed_values(
        request_df["request_purpose"].tolist(),
        config.allowed_values["request_purpose"],
        field_name="raw_access_requests.request_purpose",
    )
    assert_allowed_values(
        request_df["data_classification"].tolist(),
        config.allowed_values["data_classification"],
        field_name="raw_access_requests.data_classification",
    )
    assert_allowed_values(
        request_df["request_status"].tolist(),
        config.allowed_values["request_status"],
        field_name="raw_access_requests.request_status",
    )

    target_status_counts = config.request_review_config["request_status_targets"]
    actual_status_counts = (
        request_df["request_status"].value_counts(dropna=False).to_dict()
    )
    for status, expected_count in target_status_counts.items():
        actual_count = int(actual_status_counts.get(status, 0))
        if actual_count != int(expected_count):
            raise ValidationError(
                "raw_access_requests exact status targets are not satisfied; "
                f"status={status!r}, expected={expected_count}, got={actual_count}."
            )

    user_lookup: dict[str, dict[str, str]] = {
        _require_str(row.user_id, field_name="raw_user_directory.user_id"): {
            "employment_status": _require_str(
                row.employment_status,
                field_name="raw_user_directory.employment_status",
            ),
        }
        for row in user_df.itertuples(index=False)
    }

    pending_mask = request_df["request_status"] == "pending"
    approved_mask = request_df["request_status"] == "approved"
    rejected_mask = request_df["request_status"] == "rejected"
    reviewed_mask = approved_mask | rejected_mask

    if request_df.loc[pending_mask, "reviewed_at"].notna().any():
        raise ValidationError("Pending rows must have null reviewed_at.")
    if request_df.loc[pending_mask, "reviewed_by_user_id"].notna().any():
        raise ValidationError("Pending rows must have null reviewed_by_user_id.")
    if request_df.loc[pending_mask, "review_comment_text"].notna().any():
        raise ValidationError("Pending rows must have null review_comment_text.")

    if request_df.loc[reviewed_mask, "reviewed_at"].isna().any():
        raise ValidationError("Reviewed rows must have non-null reviewed_at.")
    if request_df.loc[reviewed_mask, "reviewed_by_user_id"].isna().any():
        raise ValidationError("Reviewed rows must have non-null reviewed_by_user_id.")
    if request_df.loc[rejected_mask, "review_comment_text"].isna().any():
        raise ValidationError("Rejected rows must have non-null review_comment_text.")

    for row in request_df.itertuples(index=False):
        request_id = _require_str(
            row.request_id,
            field_name="raw_access_requests.request_id",
        )
        requester_user_id = _require_str(
            row.requester_user_id,
            field_name="raw_access_requests.requester_user_id",
        )
        requested_at = _require_utc_datetime(
            row.requested_at,
            field_name="raw_access_requests.requested_at",
        )
        business_text = _require_str(
            row.business_justification_text,
            field_name="raw_access_requests.business_justification_text",
        )
        request_status = _require_str(
            row.request_status,
            field_name="raw_access_requests.request_status",
        )

        if user_lookup[requester_user_id]["employment_status"] != "active":
            raise ValidationError(
                "Inactive users must not appear as requesters in final raw_access_requests; "
                f"request_id={request_id!r}, requester_user_id={requester_user_id!r}."
            )

        if business_text != business_text.strip():
            raise ValidationError(
                "business_justification_text must not contain leading/trailing spaces."
            )
        if not business_text:
            raise ValidationError("business_justification_text must not be empty.")

        if request_status in {"approved", "rejected"}:
            reviewed_at = _require_utc_datetime(
                row.reviewed_at,
                field_name="raw_access_requests.reviewed_at",
            )
            reviewed_by_user_id = _require_str(
                row.reviewed_by_user_id,
                field_name="raw_access_requests.reviewed_by_user_id",
            )

            if reviewed_at <= requested_at:
                raise ValidationError(
                    "reviewed_at must be strictly after requested_at for reviewed rows; "
                    f"request_id={request_id!r}."
                )

            if user_lookup[reviewed_by_user_id]["employment_status"] != "active":
                raise ValidationError(
                    "Inactive users must not appear as reviewers in final raw_access_requests; "
                    f"request_id={request_id!r}, reviewed_by_user_id={reviewed_by_user_id!r}."
                )

            if reviewed_by_user_id == requester_user_id:
                raise ValidationError(
                    "Self review is forbidden in final raw_access_requests; "
                    f"request_id={request_id!r}, user_id={reviewed_by_user_id!r}."
                )

        review_comment_value = row.review_comment_text
        if review_comment_value is not None and not pd.isna(review_comment_value):
            review_comment = _require_str(
                review_comment_value,
                field_name="raw_access_requests.review_comment_text",
            )
            if review_comment != review_comment.strip():
                raise ValidationError(
                    "review_comment_text must not contain leading/trailing spaces."
                )
            if not review_comment:
                raise ValidationError(
                    "review_comment_text must not be empty when present."
                )

    expected_order_keys = list(
        request_df.sort_values(
            by=["requested_at", "request_id"],
            kind="stable",
        )[["requested_at", "request_id"]].itertuples(index=False, name=None)
    )
    actual_order_keys = list(
        request_df[["requested_at", "request_id"]].itertuples(index=False, name=None)
    )
    if actual_order_keys != expected_order_keys:
        raise ValidationError(
            "raw_access_requests row order must be sorted by requested_at, request_id."
        )
