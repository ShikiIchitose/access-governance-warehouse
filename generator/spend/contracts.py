from __future__ import annotations

import math

import pandas as pd

from generator.types import RuntimeConfig


def assign_licensed_seats(
    billed_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    if billed_df.empty:
        result_df = billed_df.copy()
        result_df["licensed_seats"] = pd.Series(dtype="int64")
        return result_df

    seat_config = config.spend_generation_config["licensed_seats"]

    approved_multiplier_lookup = seat_config[
        "seat_multiplier_from_approved_users_by_tool_category"
    ]
    active_multiplier_lookup = seat_config[
        "seat_multiplier_from_active_users_by_tool_category"
    ]
    buffer_lookup = seat_config["seat_buffer_by_tool_category"]
    min_seats = int(seat_config["min_licensed_seats_if_billed"])
    max_seats = int(seat_config["max_licensed_seats_global"])
    team_size_cap_enabled = bool(seat_config["team_size_cap"])

    licensed_seats: list[int] = []
    for row in billed_df.itertuples(index=False):
        tool_category = str(row.tool_category)
        approved_users_total = int(row.approved_users_total)
        active_users_total = int(row.active_users_total)
        team_size = int(row.team_size)

        approved_candidate = math.ceil(
            float(approved_multiplier_lookup[tool_category]) * approved_users_total
        )
        active_candidate = math.ceil(
            float(active_multiplier_lookup[tool_category]) * active_users_total
        ) + int(buffer_lookup[tool_category])

        realized_seats = max(
            min_seats,
            approved_candidate,
            active_candidate,
        )
        realized_seats = min(realized_seats, max_seats)

        if team_size_cap_enabled:
            realized_seats = min(realized_seats, team_size)

        licensed_seats.append(int(realized_seats))

    result_df = billed_df.copy()
    result_df["licensed_seats"] = pd.Series(licensed_seats, index=result_df.index)

    return result_df
