from __future__ import annotations

from dataclasses import replace

import pandas as pd

from generator.types import RequestSkeleton, RuntimeConfig


def _ordered_team_month_tool_df(team_month_tool_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = (
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "team_order",
        "tool_code",
        "tool_order",
        "request_count",
    )
    missing_columns = [
        column
        for column in required_columns
        if column not in team_month_tool_df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"team_month_tool_df is missing required columns: {missing_columns}"
        )

    return team_month_tool_df.sort_values(
        by=["request_month", "month_index", "team_order", "tool_order"],
        kind="stable",
    ).reset_index(drop=True)


def expand_request_skeletons(team_month_tool_df: pd.DataFrame) -> list[RequestSkeleton]:
    ordered_df = _ordered_team_month_tool_df(team_month_tool_df)

    skeletons: list[RequestSkeleton] = []
    for row in ordered_df.itertuples(index=False):
        request_count = int(row.request_count)
        if request_count < 0:
            raise ValueError(
                "team_month_tool_df.request_count must be >= 0 for all rows."
            )

        for within_group_request_index in range(1, request_count + 1):
            skeletons.append(
                RequestSkeleton(
                    request_month=row.request_month,
                    month_index=int(row.month_index),
                    team_name=row.team_name,
                    department_name=row.department_name,
                    team_order=int(row.team_order),
                    tool_code=row.tool_code,
                    tool_order=int(row.tool_order),
                    within_group_request_index=within_group_request_index,
                )
            )

    return skeletons


def assign_request_ids(
    skeletons: list[RequestSkeleton],
    config: RuntimeConfig,
) -> list[RequestSkeleton]:
    prefix = str(config.request_volume_config["request_id_prefix"])
    zero_pad = int(config.request_volume_config["request_id_zero_pad"])

    assigned: list[RequestSkeleton] = []
    for global_request_rank, skeleton in enumerate(skeletons, start=1):
        request_id = f"{prefix}{global_request_rank:0{zero_pad}d}"
        assigned.append(
            replace(
                skeleton,
                global_request_rank=global_request_rank,
                request_id=request_id,
            )
        )

    return assigned


def build_request_skeleton_df(
    skeletons: list[RequestSkeleton],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for skeleton in skeletons:
        if skeleton.request_id is None:
            raise ValueError("request_id must be assigned before DataFrame assembly.")
        if skeleton.global_request_rank is None:
            raise ValueError(
                "global_request_rank must be assigned before DataFrame assembly."
            )

        rows.append(
            {
                "request_id": skeleton.request_id,
                "request_month": skeleton.request_month,
                "month_index": skeleton.month_index,
                "team_name": skeleton.team_name,
                "department_name": skeleton.department_name,
                "tool_code": skeleton.tool_code,
                "within_group_request_index": skeleton.within_group_request_index,
                "global_request_rank": skeleton.global_request_rank,
                "team_order": skeleton.team_order,
                "tool_order": skeleton.tool_order,
            }
        )

    return pd.DataFrame.from_records(
        rows,
        columns=(
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
        ),
    )
