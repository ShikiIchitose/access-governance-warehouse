from __future__ import annotations

from typing import Any, Mapping

from generator.helpers.validation import ValidationError
from generator.types import OrgSeed, OrgTeam, RuntimeConfig

_REQUIRED_TEAM_KEYS = ("team_name", "department_name", "size")


def _require_non_empty_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return normalized


def _require_positive_int(value: Any, *, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be positive.")
    return value


def build_team_order_lookup(org_seed: OrgSeed) -> dict[str, int]:
    return {team.team_name: team.team_order for team in org_seed.teams}


def build_team_to_department_lookup(org_seed: OrgSeed) -> dict[str, str]:
    return {team.team_name: team.department_name for team in org_seed.teams}


def build_org_seed(config: RuntimeConfig) -> OrgSeed:
    org_config = config.org_config

    departments_raw = org_config.get("departments")
    teams_raw = org_config.get("teams")

    if not isinstance(departments_raw, (list, tuple)) or not departments_raw:
        raise ValidationError(
            "ORG_CONFIG['departments'] must be a non-empty list or tuple."
        )
    if not isinstance(teams_raw, (list, tuple)) or not teams_raw:
        raise ValidationError("ORG_CONFIG['teams'] must be a non-empty list or tuple.")

    departments = tuple(
        _require_non_empty_string(value, field_name="ORG_CONFIG.departments[]")
        for value in departments_raw
    )

    if len(set(departments)) != len(departments):
        raise ValidationError("ORG_CONFIG['departments'] must not contain duplicates.")

    teams: list[OrgTeam] = []
    seen_team_names: set[str] = set()

    for team_order, raw_team in enumerate(teams_raw):
        if not isinstance(raw_team, Mapping):
            raise ValidationError("Every ORG_CONFIG team entry must be a mapping.")

        missing_keys = [key for key in _REQUIRED_TEAM_KEYS if key not in raw_team]
        if missing_keys:
            raise ValidationError(
                f"ORG_CONFIG team entry is missing required keys: {missing_keys}"
            )

        team_name = _require_non_empty_string(
            raw_team["team_name"],
            field_name="ORG_CONFIG.teams[].team_name",
        )
        department_name = _require_non_empty_string(
            raw_team["department_name"],
            field_name="ORG_CONFIG.teams[].department_name",
        )
        size = _require_positive_int(
            raw_team["size"],
            field_name="ORG_CONFIG.teams[].size",
        )

        if team_name in seen_team_names:
            raise ValidationError(f"Duplicate team_name detected: {team_name}")
        seen_team_names.add(team_name)

        if department_name not in departments:
            raise ValidationError(
                f"Team {team_name!r} references undeclared department {department_name!r}."
            )

        teams.append(
            OrgTeam(
                team_name=team_name,
                department_name=department_name,
                size=size,
                team_order=team_order,
            )
        )

    observed_departments = {team.department_name for team in teams}
    missing_departments = set(departments) - observed_departments
    if missing_departments:
        raise ValidationError(
            f"ORG_CONFIG declares departments with no teams: {sorted(missing_departments)}"
        )

    total_users = sum(team.size for team in teams)
    expected_users = config.raw_targets.get("raw_user_directory_rows")
    if expected_users is None:
        raise ValidationError("Missing raw_user_directory_rows in raw_targets.")
    if total_users != expected_users:
        raise ValidationError(
            "ORG_CONFIG team sizes do not match raw_user_directory_rows: "
            f"{total_users} != {expected_users}"
        )

    org_seed = OrgSeed(
        departments=departments,
        teams=tuple(teams),
        team_order_lookup={team.team_name: team.team_order for team in teams},
        team_to_department_lookup={
            team.team_name: team.department_name for team in teams
        },
        total_users=total_users,
    )
    return org_seed
