from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any, TypedDict, cast

import pandas as pd

from generator.helpers.validation import ValidationError
from generator.requests.requester_assignment import (
    build_requester_user_lookup,
    choose_requester_candidate,
    get_active_requester_candidate_user_ids,
    score_requester_candidates,
)
from generator.types import RuntimeConfig, UserUniverses


class DuplicatePolicyConfig(TypedDict):
    duplicate_unit: tuple[str, ...] | list[str]
    sequence_sort_keys: tuple[str, ...] | list[str]
    max_requests_per_user_tool_pair: int
    same_calendar_month_duplicates_forbidden: bool
    later_request_after_approved_forbidden: bool
    later_request_after_pending_forbidden: bool
    all_non_final_requests_in_multi_request_sequence_must_be_rejected: bool
    max_pending_requests_per_user_tool_pair: int
    enforcement_strategy: dict[str, object]


class SequenceRecord(TypedDict):
    request_id: str
    request_month: object
    requested_at: object
    request_status: str
    requester_user_id: str
    tool_code: str


def _duplicate_policy_config(config: RuntimeConfig) -> DuplicatePolicyConfig:
    return cast(DuplicatePolicyConfig, dict(config.request_duplicate_policy_config))


def _sequence_sort_keys(config: RuntimeConfig) -> list[str]:
    return list(config.request_duplicate_policy_config["sequence_sort_keys"])


def _request_month_key(value: object) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _is_candidate_feasible_for_row(
    row: Any,
    candidate_user_id: str,
    sequences_by_pair: Mapping[tuple[str, str], list[SequenceRecord]],
    config: RuntimeConfig,
) -> bool:
    policy = _duplicate_policy_config(config)
    pair_key = (candidate_user_id, str(row.tool_code))
    prior_sequence = sequences_by_pair.get(pair_key, [])

    if len(prior_sequence) >= policy["max_requests_per_user_tool_pair"]:
        return False

    if policy["same_calendar_month_duplicates_forbidden"]:
        current_month_key = _request_month_key(row.request_month)
        prior_month_keys = {
            _request_month_key(item["request_month"]) for item in prior_sequence
        }
        if current_month_key in prior_month_keys:
            return False

    if policy["later_request_after_approved_forbidden"]:
        if any(item["request_status"] == "approved" for item in prior_sequence):
            return False

    if policy["later_request_after_pending_forbidden"]:
        if any(item["request_status"] == "pending" for item in prior_sequence):
            return False

    if policy["all_non_final_requests_in_multi_request_sequence_must_be_rejected"]:
        if prior_sequence and any(
            item["request_status"] != "rejected" for item in prior_sequence
        ):
            return False

    pending_count = sum(
        1 for item in prior_sequence if item["request_status"] == "pending"
    )
    if str(row.request_status) == "pending":
        if pending_count >= policy["max_pending_requests_per_user_tool_pair"]:
            return False

    return True


def _make_sequence_record(row: Any, requester_user_id: str) -> SequenceRecord:
    return {
        "request_id": str(row.request_id),
        "request_month": row.request_month,
        "requested_at": row.requested_at,
        "request_status": str(row.request_status),
        "requester_user_id": requester_user_id,
        "tool_code": str(row.tool_code),
    }


def _assert_duplicate_policy_feasibility(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    config: RuntimeConfig,
) -> None:
    active_users_by_team = (
        user_df.loc[user_df["employment_status"] == "active"]
        .groupby("team_name", sort=False)["user_id"]
        .nunique()
        .to_dict()
    )

    # Necessary condition 1:
    # approved + pending per (team, tool) must not exceed active users in team.
    terminal_df = request_df.loc[
        request_df["request_status"].isin(["approved", "pending"])
    ].copy()
    terminal_counts = (
        terminal_df.groupby(["team_name", "tool_code"], sort=False).size().to_dict()
    )

    for (team_name, tool_code), terminal_count in terminal_counts.items():
        active_capacity = int(active_users_by_team.get(team_name, 0))
        if int(terminal_count) > active_capacity:
            raise ValidationError(
                "Duplicate-policy feasibility failed before reconciliation: "
                "approved+pending requests for a (team_name, tool_code) cell exceed "
                "the number of active users in that team; "
                f"team_name={team_name!r}, "
                f"tool_code={tool_code!r}, "
                f"approved_plus_pending={int(terminal_count)}, "
                f"active_users={active_capacity}."
            )

    # Necessary condition 2:
    # same-month duplicate forbidden implies one team-tool-month cannot exceed active users.
    month_counts = (
        request_df.groupby(["request_month", "team_name", "tool_code"], sort=False)
        .size()
        .to_dict()
    )

    for (request_month, team_name, tool_code), request_count in month_counts.items():
        active_capacity = int(active_users_by_team.get(team_name, 0))
        if int(request_count) > active_capacity:
            raise ValidationError(
                "Duplicate-policy feasibility failed before reconciliation: "
                "same-month request volume for a (request_month, team_name, tool_code) "
                "cell exceeds the number of active users in that team; "
                f"request_month={request_month!r}, "
                f"team_name={team_name!r}, "
                f"tool_code={tool_code!r}, "
                f"request_count={int(request_count)}, "
                f"active_users={active_capacity}."
            )

    # Necessary condition 3:
    # max 3 requests per user-tool pair implies team-tool total cannot exceed 3 * active users.
    total_counts = (
        request_df.groupby(["team_name", "tool_code"], sort=False).size().to_dict()
    )
    max_requests_per_pair = int(
        config.request_duplicate_policy_config["max_requests_per_user_tool_pair"]
    )

    for (team_name, tool_code), request_count in total_counts.items():
        active_capacity = int(active_users_by_team.get(team_name, 0))
        max_capacity = max_requests_per_pair * active_capacity
        if int(request_count) > max_capacity:
            raise ValidationError(
                "Duplicate-policy feasibility failed before reconciliation: "
                "total requests for a (team_name, tool_code) cell exceed the "
                "maximum pair-capacity implied by max_requests_per_user_tool_pair; "
                f"team_name={team_name!r}, "
                f"tool_code={tool_code!r}, "
                f"request_count={int(request_count)}, "
                f"max_capacity={max_capacity}."
            )


def reconcile_duplicate_request_policy(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    user_universes: UserUniverses,
    config: RuntimeConfig,
) -> pd.DataFrame:
    if request_df.empty:
        return request_df.copy()

    working_df = request_df.copy()
    chronological_df = working_df.sort_values(
        by=_sequence_sort_keys(config),
        kind="stable",
    ).copy()

    _assert_duplicate_policy_feasibility(
        working_df,
        user_df,
        config,
    )

    user_lookup = build_requester_user_lookup(user_df)

    month_request_counts: dict[tuple[object, str], int] = defaultdict(int)
    same_tool_request_counts: dict[tuple[str, str], int] = defaultdict(int)
    sequences_by_pair: dict[tuple[str, str], list[SequenceRecord]] = defaultdict(list)

    reassignment_count = 0

    for row in chronological_df.itertuples():
        original_user_id = str(row.requester_user_id)

        candidate_user_ids = get_active_requester_candidate_user_ids(
            row.team_name,
            user_universes,
        )

        feasible_candidate_user_ids = tuple(
            user_id
            for user_id in candidate_user_ids
            if _is_candidate_feasible_for_row(
                row,
                user_id,
                sequences_by_pair,
                config,
            )
        )

        if not feasible_candidate_user_ids:
            raise ValidationError(
                "Duplicate-policy reconciliation failed because no feasible "
                "alternate requester exists; "
                f"request_id={row.request_id!r}, "
                f"team_name={row.team_name!r}, "
                f"tool_code={row.tool_code!r}, "
                f"request_status={row.request_status!r}."
            )

        if original_user_id in feasible_candidate_user_ids:
            selected_user_id = original_user_id
        else:
            candidate_scores = score_requester_candidates(
                row,
                feasible_candidate_user_ids,
                user_lookup,
                month_request_counts,
                same_tool_request_counts,
                config,
                jitter_namespace="duplicate_policy_reassignment_jitter",
            )
            selected_user_id = choose_requester_candidate(
                row,
                feasible_candidate_user_ids,
                candidate_scores,
                config,
                choice_namespace="duplicate_policy_reassignment_choice",
            )
            reassignment_count += 1

        working_df.at[row.Index, "requester_user_id"] = selected_user_id

        month_request_counts[(row.request_month, selected_user_id)] += 1
        same_tool_request_counts[(selected_user_id, row.tool_code)] += 1
        sequences_by_pair[(selected_user_id, row.tool_code)].append(
            _make_sequence_record(row, selected_user_id)
        )

    working_df.attrs["duplicate_policy_reassignment_count"] = reassignment_count
    return working_df
