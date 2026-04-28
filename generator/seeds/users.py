from __future__ import annotations

from dataclasses import replace
from itertools import product
from types import MappingProxyType

import pandas as pd

from generator.helpers.deterministic import make_hash_int
from generator.helpers.sorting import stable_sort_with_order_lookups
from generator.types import OrgSeed, RuntimeConfig, UserSlot, UserUniverses

RAW_USER_DIRECTORY_COLUMNS = (
    "user_id",
    "user_name",
    "user_email",
    "team_name",
    "department_name",
    "job_level",
    "employment_status",
)


def _require_completed_slots(
    slots: list[UserSlot],
    *,
    required_fields: tuple[str, ...],
) -> None:
    for slot in slots:
        missing = [field for field in required_fields if getattr(slot, field) is None]
        if missing:
            raise ValueError(
                "user slot is not fully realized; "
                f"missing fields={missing}, "
                f"team={slot.team_name!r}, slot={slot.within_team_slot_order}"
            )


def _require_unique_non_empty_strings(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> None:
    if not values:
        raise ValueError(f"{field_name} must not be empty.")
    if any(not value or not value.strip() for value in values):
        raise ValueError(f"{field_name} must not contain empty strings.")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must contain unique values.")


def build_user_slots(org_seed: OrgSeed) -> list[UserSlot]:
    slots: list[UserSlot] = []

    for team in org_seed.teams:
        for within_team_slot_order in range(1, team.size + 1):
            slots.append(
                UserSlot(
                    team_name=team.team_name,
                    department_name=team.department_name,
                    team_order=team.team_order,
                    within_team_slot_order=within_team_slot_order,
                )
            )

    return slots


def assign_job_levels(
    slots: list[UserSlot],
    config: RuntimeConfig,
) -> list[UserSlot]:
    counts_by_team = config.user_profile_config["job_level"]["job_level_counts_by_team"]
    job_level_values = set(config.allowed_values["job_level"])

    assigned_by_key: dict[tuple[str, int], str] = {}

    for team_name, team_counts in counts_by_team.items():
        unknown_levels = set(team_counts) - job_level_values
        if unknown_levels:
            raise ValueError(
                f"Unknown job levels for team {team_name!r}: {sorted(unknown_levels)}"
            )

        director_count = int(team_counts["director"])
        manager_count = int(team_counts["manager"])
        individual_contributor_count = int(team_counts["individual_contributor"])

        team_slots = [slot for slot in slots if slot.team_name == team_name]
        if len(team_slots) != (
            director_count + manager_count + individual_contributor_count
        ):
            raise ValueError(
                f"Job-level quotas do not sum to team size for team {team_name!r}."
            )

        for index, slot in enumerate(team_slots, start=1):
            if index <= director_count:
                job_level = "director"
            elif index <= director_count + manager_count:
                job_level = "manager"
            else:
                job_level = "individual_contributor"

            assigned_by_key[(slot.team_name, slot.within_team_slot_order)] = job_level

    return [
        replace(
            slot,
            job_level=assigned_by_key[(slot.team_name, slot.within_team_slot_order)],
        )
        for slot in slots
    ]


def assign_employment_status(
    slots: list[UserSlot],
    config: RuntimeConfig,
) -> list[UserSlot]:
    _require_completed_slots(slots, required_fields=("job_level",))

    counts_by_team_and_level = config.user_profile_config["employment_status"][
        "employment_status_counts_by_team_and_job_level"
    ]
    status_values = set(config.allowed_values["employment_status"])

    assigned_by_key: dict[tuple[str, int], str] = {}

    for team_name, level_map in counts_by_team_and_level.items():
        team_slots = [slot for slot in slots if slot.team_name == team_name]

        for job_level, status_counts in level_map.items():
            unknown_statuses = set(status_counts) - status_values
            if unknown_statuses:
                raise ValueError(
                    f"Unknown employment statuses for team {team_name!r}, "
                    f"job_level {job_level!r}: {sorted(unknown_statuses)}"
                )

            subgroup_slots = [
                slot for slot in team_slots if slot.job_level == job_level
            ]
            subgroup_slots = sorted(
                subgroup_slots,
                key=lambda slot: slot.within_team_slot_order,
            )

            inactive_count = int(status_counts["inactive"])
            active_count = int(status_counts["active"])

            if len(subgroup_slots) != inactive_count + active_count:
                raise ValueError(
                    "Employment-status quotas do not sum to subgroup size for "
                    f"team={team_name!r}, job_level={job_level!r}."
                )

            for index, slot in enumerate(subgroup_slots, start=1):
                employment_status = "inactive" if index <= inactive_count else "active"
                assigned_by_key[(slot.team_name, slot.within_team_slot_order)] = (
                    employment_status
                )

    return [
        replace(
            slot,
            employment_status=assigned_by_key[
                (slot.team_name, slot.within_team_slot_order)
            ],
        )
        for slot in slots
    ]


def assign_user_ids(slots: list[UserSlot]) -> list[UserSlot]:
    _require_completed_slots(
        slots,
        required_fields=("job_level", "employment_status"),
    )

    return [
        replace(
            slot,
            global_user_rank=index,
            user_id=f"usr_{index:04d}",
        )
        for index, slot in enumerate(slots, start=1)
    ]


def _select_name_pairs(
    *,
    config: RuntimeConfig,
    n_required: int,
) -> list[tuple[str, str]]:
    given_name_pool = tuple(config.user_name_config["given_name_pool"])
    family_name_pool = tuple(config.user_name_config["family_name_pool"])

    _require_unique_non_empty_strings(
        given_name_pool,
        field_name="USER_NAME_CONFIG['given_name_pool']",
    )
    _require_unique_non_empty_strings(
        family_name_pool,
        field_name="USER_NAME_CONFIG['family_name_pool']",
    )

    candidate_pairs = list(product(given_name_pool, family_name_pool))
    if len(candidate_pairs) < n_required:
        raise ValueError(
            "Name-pair candidate space is too small for the required user count."
        )

    ranked_candidates: list[tuple[tuple[int, int], str, str]] = []

    for original_index, (given_name, family_name) in enumerate(candidate_pairs):
        rank_key = (
            make_hash_int(
                given_name,
                family_name,
                seed=config.seed,
                namespace="user_name_pair",
            ),
            original_index,
        )
        ranked_candidates.append((rank_key, given_name, family_name))

    ranked_candidates.sort(key=lambda item: item[0])

    return [
        (given_name, family_name)
        for _, given_name, family_name in ranked_candidates[:n_required]
    ]


def assign_user_names(
    slots: list[UserSlot],
    config: RuntimeConfig,
) -> list[UserSlot]:
    _require_completed_slots(
        slots,
        required_fields=("global_user_rank", "user_id"),
    )

    selected_pairs = _select_name_pairs(
        config=config,
        n_required=len(slots),
    )

    assigned_slots: list[UserSlot] = []
    for slot, (given_name, family_name) in zip(slots, selected_pairs, strict=True):
        assigned_slots.append(
            replace(
                slot,
                given_name=given_name,
                family_name=family_name,
                user_name=f"{given_name} {family_name}",
            )
        )

    return assigned_slots


def assign_user_emails(
    slots: list[UserSlot],
    config: RuntimeConfig,
) -> list[UserSlot]:
    _require_completed_slots(
        slots,
        required_fields=("global_user_rank", "user_name", "given_name", "family_name"),
    )

    email_domain = str(config.user_email_config["domain"]).strip().lower()
    if not email_domain:
        raise ValueError("USER_EMAIL_CONFIG['domain'] must be a non-empty string.")

    assigned_slots: list[UserSlot] = []
    for slot in slots:
        assert slot.global_user_rank is not None
        assert slot.given_name is not None
        assert slot.family_name is not None

        rank_suffix = f"{slot.global_user_rank:04d}"
        local_part = (
            f"{slot.given_name.lower()}.{slot.family_name.lower()}.{rank_suffix}"
        )
        user_email = f"{local_part}@{email_domain}"

        assigned_slots.append(
            replace(
                slot,
                user_email=user_email,
            )
        )

    return assigned_slots


def build_user_directory_df(
    slots: list[UserSlot],
    org_seed: OrgSeed,
) -> pd.DataFrame:
    _require_completed_slots(
        slots,
        required_fields=(
            "global_user_rank",
            "job_level",
            "employment_status",
            "user_id",
            "user_name",
            "user_email",
        ),
    )

    records = []
    for slot in slots:
        records.append(
            {
                "user_id": slot.user_id,
                "user_name": slot.user_name,
                "user_email": slot.user_email,
                "team_name": slot.team_name,
                "department_name": slot.department_name,
                "job_level": slot.job_level,
                "employment_status": slot.employment_status,
                "__within_team_slot_order": slot.within_team_slot_order,
            }
        )

    user_df = pd.DataFrame.from_records(records)
    user_df = stable_sort_with_order_lookups(
        user_df,
        by=("team_name", "__within_team_slot_order", "user_id"),
        order_lookups={"team_name": org_seed.team_order_lookup},
        ignore_index=True,
    )
    user_df = user_df.drop(columns="__within_team_slot_order")
    user_df = user_df.loc[:, list(RAW_USER_DIRECTORY_COLUMNS)].copy()

    return user_df


def derive_user_universes(user_df: pd.DataFrame) -> UserUniverses:
    team_order = tuple(user_df["team_name"].drop_duplicates().tolist())

    all_user_ids = tuple(user_df["user_id"].tolist())

    active_df = user_df.loc[user_df["employment_status"] == "active"].copy()
    inactive_df = user_df.loc[user_df["employment_status"] == "inactive"].copy()

    active_user_ids = tuple(active_df["user_id"].tolist())
    inactive_user_ids = tuple(inactive_df["user_id"].tolist())

    active_requester_by_team: dict[str, tuple[str, ...]] = {}
    reviewer_eligible_by_team: dict[str, tuple[str, ...]] = {}

    for team_name in team_order:
        team_active_ids = tuple(
            active_df.loc[active_df["team_name"] == team_name, "user_id"].tolist()
        )
        active_requester_by_team[team_name] = team_active_ids
        reviewer_eligible_by_team[team_name] = team_active_ids

    return UserUniverses(
        all_user_ids=all_user_ids,
        active_user_ids=active_user_ids,
        inactive_user_ids=inactive_user_ids,
        active_requester_user_ids_by_team=MappingProxyType(active_requester_by_team),
        reviewer_eligible_user_ids=active_user_ids,
        reviewer_eligible_user_ids_by_team=MappingProxyType(reviewer_eligible_by_team),
    )


def build_user_directory(
    org_seed: OrgSeed,
    config: RuntimeConfig,
) -> tuple[pd.DataFrame, UserUniverses]:
    slots = build_user_slots(org_seed)
    slots = assign_job_levels(slots, config)
    slots = assign_employment_status(slots, config)
    slots = assign_user_ids(slots)
    slots = assign_user_names(slots, config)
    slots = assign_user_emails(slots, config)

    user_df = build_user_directory_df(slots, org_seed)
    user_universes = derive_user_universes(user_df)

    return user_df, user_universes
