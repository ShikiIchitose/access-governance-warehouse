from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any, TypedDict, cast

import pandas as pd

from generator.helpers.deterministic import (
    deterministic_weighted_choice,
    make_deterministic_jitter,
)
from generator.helpers.validation import ValidationError
from generator.types import RuntimeConfig, UserUniverses


class RequesterAssignmentConfig(TypedDict):
    eligibility_rules: dict[str, object]
    job_level_multipliers: dict[str, float]
    monthly_request_load_multipliers: dict[str, float]
    same_tool_repeat_multipliers: dict[str, float]
    deterministic_jitter_range: tuple[float, float]
    selection_method: str


def _requester_assignment_config(config: RuntimeConfig) -> dict[str, object]:
    return dict(config.request_submission_config["requester_assignment"])


def _monthly_request_load_bucket(count: int) -> str:
    if count >= 5:
        return "5_plus"
    return str(count)


def _same_tool_repeat_bucket(count: int) -> str:
    if count >= 3:
        return "3_plus"
    return str(count)


def build_requester_user_lookup(user_df: pd.DataFrame) -> dict[str, dict[str, str]]:
    return {
        str(row.user_id): {
            "team_name": str(row.team_name),
            "department_name": str(row.department_name),
            "job_level": str(row.job_level),
            "employment_status": str(row.employment_status),
        }
        for row in user_df.itertuples(index=False)
    }


def get_active_requester_candidate_user_ids(
    team_name: str,
    user_universes: UserUniverses,
) -> tuple[str, ...]:
    candidate_user_ids = tuple(
        user_universes.active_requester_user_ids_by_team.get(team_name, ())
    )
    if not candidate_user_ids:
        raise ValidationError(
            f"No active requester candidates available for team {team_name!r}."
        )
    return candidate_user_ids


def score_requester_candidates(
    row: Any,
    candidate_user_ids: tuple[str, ...],
    user_lookup: Mapping[str, Mapping[str, str]],
    month_request_counts: Mapping[tuple[object, str], int],
    same_tool_request_counts: Mapping[tuple[str, str], int],
    config: RuntimeConfig,
    *,
    jitter_namespace: str = "requester_assignment_jitter",
) -> list[float]:
    requester_config = cast(
        RequesterAssignmentConfig,
        _requester_assignment_config(config),
    )
    low, high = requester_config["deterministic_jitter_range"]

    candidate_scores: list[float] = []

    for user_id in candidate_user_ids:
        user_meta = user_lookup[user_id]

        if str(user_meta["employment_status"]) != "active":
            raise ValidationError(
                f"Inactive user {user_id!r} appeared in the active requester universe."
            )

        if str(user_meta["team_name"]) != row.team_name:
            raise ValidationError(
                "Requester candidate universe violates same-team eligibility; "
                f"row_team={row.team_name!r}, candidate_team={user_meta['team_name']!r}."
            )

        job_level = str(user_meta["job_level"])
        monthly_load = month_request_counts.get((row.request_month, user_id), 0)
        same_tool_load = same_tool_request_counts.get((user_id, row.tool_code), 0)

        job_level_multiplier = float(
            requester_config["job_level_multipliers"][job_level]
        )
        monthly_load_multiplier = float(
            requester_config["monthly_request_load_multipliers"][
                _monthly_request_load_bucket(monthly_load)
            ]
        )
        same_tool_multiplier = float(
            requester_config["same_tool_repeat_multipliers"][
                _same_tool_repeat_bucket(same_tool_load)
            ]
        )
        jitter = make_deterministic_jitter(
            row.request_id,
            user_id,
            row.request_month,
            row.tool_code,
            low=low,
            high=high,
            seed=config.seed,
            namespace=jitter_namespace,
        )

        candidate_scores.append(
            job_level_multiplier
            * monthly_load_multiplier
            * same_tool_multiplier
            * jitter
        )

    return candidate_scores


def choose_requester_candidate(
    row: Any,
    candidate_user_ids: tuple[str, ...],
    candidate_scores: list[float],
    config: RuntimeConfig,
    *,
    choice_namespace: str = "requester_assignment_choice",
) -> str:
    if not candidate_user_ids:
        raise ValidationError(
            f"No requester candidates available for request_id={row.request_id!r}."
        )

    return deterministic_weighted_choice(
        candidate_user_ids,
        candidate_scores,
        row.request_id,
        row.request_month,
        row.team_name,
        row.tool_code,
        row.within_group_request_index,
        seed=config.seed,
        namespace=choice_namespace,
    )


def assign_requesters(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    user_universes: UserUniverses,
    config: RuntimeConfig,
) -> pd.DataFrame:
    user_lookup = build_requester_user_lookup(user_df)

    month_request_counts: dict[tuple[object, str], int] = defaultdict(int)
    same_tool_request_counts: dict[tuple[str, str], int] = defaultdict(int)

    assigned_requesters: list[str] = []

    for row in request_df.itertuples(index=False):
        candidate_user_ids = get_active_requester_candidate_user_ids(
            row.team_name,
            user_universes,
        )
        candidate_scores = score_requester_candidates(
            row,
            candidate_user_ids,
            user_lookup,
            month_request_counts,
            same_tool_request_counts,
            config,
        )
        selected_user_id = choose_requester_candidate(
            row,
            candidate_user_ids,
            candidate_scores,
            config,
        )

        assigned_requesters.append(selected_user_id)
        month_request_counts[(row.request_month, selected_user_id)] += 1
        same_tool_request_counts[(selected_user_id, row.tool_code)] += 1

    enriched_df = request_df.copy()
    enriched_df["requester_user_id"] = assigned_requesters
    return enriched_df
