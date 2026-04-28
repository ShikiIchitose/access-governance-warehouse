from __future__ import annotations

import pandas as pd

from generator.helpers.dates import (
    iter_dates_in_month,
    month_position_bucket,
    weekday_name,
)
from generator.helpers.deterministic import (
    deterministic_weighted_choice,
    make_deterministic_jitter,
)
from generator.helpers.validation import ValidationError
from generator.types import RuntimeConfig


def _select_active_dates_for_pair_month(
    row: pd.Series,
    config: RuntimeConfig,
) -> list:
    usage_date_cfg = config.usage_generation_config["usage_date"]
    month_value = row["usage_month"]
    active_days_in_month = int(row["active_days_in_month"])

    candidate_dates = iter_dates_in_month(month_value)

    first_approved_at = row["first_approved_at"]
    if (
        row["pair_type"] == "approved_normal"
        and pd.notna(first_approved_at)
        and bool(usage_date_cfg["approved_normal_must_not_precede_first_approved_date"])
    ):
        first_allowed_date = pd.Timestamp(first_approved_at).date()
        candidate_dates = [
            value_date
            for value_date in candidate_dates
            if value_date >= first_allowed_date
        ]

    if len(candidate_dates) < active_days_in_month:
        raise ValidationError(
            "active_days_in_month exceeds realizable candidate-date capacity for the pair-month; "
            f"user_id={row['user_id']!r}, "
            f"tool_code={row['tool_code']!r}, "
            f"usage_month={month_value!r}, "
            f"pair_type={row['pair_type']!r}, "
            f"active_days_in_month={active_days_in_month}, "
            f"candidate_dates={len(candidate_dates)}."
        )

    remaining_dates = list(candidate_dates)
    selected_dates: list = []

    for draw_index in range(active_days_in_month):
        weights: list[float] = []

        for value_date in remaining_dates:
            score = float(
                usage_date_cfg["weekday_weights"][weekday_name(value_date)]
            ) * float(
                usage_date_cfg["month_position_bucket_weights"][
                    month_position_bucket(value_date)
                ]
            )

            low, high = usage_date_cfg["date_jitter_range"]
            score *= make_deterministic_jitter(
                row["user_id"],
                row["tool_code"],
                month_value.isoformat(),
                value_date.isoformat(),
                draw_index,
                "usage_date_selection",
                low=float(low),
                high=float(high),
                seed=config.seed,
                namespace="usage_date_selection",
            )

            weights.append(score)

        selected_date = deterministic_weighted_choice(
            remaining_dates,
            weights,
            row["user_id"],
            row["tool_code"],
            month_value.isoformat(),
            draw_index,
            "usage_date_draw",
            seed=config.seed,
            namespace="usage_date_draw",
        )

        selected_dates.append(selected_date)
        remaining_dates.remove(selected_date)

    selected_dates.sort()
    return selected_dates


def _realize_session_count(
    row: pd.Series,
    usage_date,
    config: RuntimeConfig,
) -> int:
    cfg = config.usage_generation_config["session_prompt_intensity"]
    base = float(cfg["session_base_by_tool_category"][str(row["tool_category"])])
    pair_mult = float(cfg["session_pair_type_multipliers"][str(row["pair_type"])])
    class_mult = float(
        cfg["session_classification_multipliers"][str(row["data_classification"])]
    )
    low, high = cfg["session_jitter_range"]
    jitter = make_deterministic_jitter(
        row["user_id"],
        row["tool_code"],
        usage_date.isoformat(),
        "session_count",
        low=float(low),
        high=float(high),
        seed=config.seed,
        namespace="session_count",
    )
    expected = base * pair_mult * class_mult * jitter
    value = int(round(expected))
    bounds = cfg["session_count_bounds"]
    return max(int(bounds["min"]), min(int(bounds["max"]), value))


def _realize_prompt_count(
    row: pd.Series,
    usage_date,
    session_count: int,
    config: RuntimeConfig,
) -> int:
    cfg = config.usage_generation_config["session_prompt_intensity"]
    base = float(cfg["prompt_base_by_tool_category"][str(row["tool_category"])])
    pair_mult = float(cfg["prompt_pair_type_multipliers"][str(row["pair_type"])])
    class_mult = float(
        cfg["prompt_classification_multipliers"][str(row["data_classification"])]
    )
    session_mult = float(cfg["prompt_multiplier_by_session_count"][int(session_count)])
    low, high = cfg["prompt_jitter_range"]
    jitter = make_deterministic_jitter(
        row["user_id"],
        row["tool_code"],
        usage_date.isoformat(),
        "prompt_count",
        low=float(low),
        high=float(high),
        seed=config.seed,
        namespace="prompt_count",
    )
    expected = base * pair_mult * class_mult * session_mult * jitter
    lower = max(int(cfg["prompt_count_bounds"]["min"]), int(session_count))
    upper = int(cfg["prompt_count_bounds"]["max"])
    value = int(round(expected))
    return max(lower, min(upper, value))


def _realize_input_tokens_total(
    row: pd.Series,
    usage_date,
    session_count: int,
    prompt_count: int,
    config: RuntimeConfig,
) -> int:
    cfg = config.usage_generation_config["token_intensity"]
    base = float(
        cfg["input_tokens_per_prompt_base_by_tool_category"][str(row["tool_category"])]
    )
    pair_mult = float(cfg["input_pair_type_multipliers"][str(row["pair_type"])])
    class_mult = float(
        cfg["input_classification_multipliers"][str(row["data_classification"])]
    )
    session_mult = float(cfg["input_session_multipliers"][int(session_count)])
    low, high = cfg["input_jitter_range"]
    jitter = make_deterministic_jitter(
        row["user_id"],
        row["tool_code"],
        usage_date.isoformat(),
        "input_tokens_total",
        low=float(low),
        high=float(high),
        seed=config.seed,
        namespace="input_tokens_total",
    )
    expected = base * pair_mult * class_mult * session_mult * prompt_count * jitter
    lower = int(prompt_count)
    upper = int(cfg["input_tokens_bounds"]["max"])
    value = int(round(expected))
    return max(lower, min(upper, value))


def _realize_output_tokens_total(
    row: pd.Series,
    usage_date,
    session_count: int,
    prompt_count: int,
    config: RuntimeConfig,
) -> int:
    cfg = config.usage_generation_config["token_intensity"]
    base = float(
        cfg["output_tokens_per_prompt_base_by_tool_category"][str(row["tool_category"])]
    )
    pair_mult = float(cfg["output_pair_type_multipliers"][str(row["pair_type"])])
    class_mult = float(
        cfg["output_classification_multipliers"][str(row["data_classification"])]
    )
    session_mult = float(cfg["output_session_multipliers"][int(session_count)])
    low, high = cfg["output_jitter_range"]
    jitter = make_deterministic_jitter(
        row["user_id"],
        row["tool_code"],
        usage_date.isoformat(),
        "output_tokens_total",
        low=float(low),
        high=float(high),
        seed=config.seed,
        namespace="output_tokens_total",
    )
    expected = base * pair_mult * class_mult * session_mult * prompt_count * jitter
    lower = int(prompt_count)
    upper = int(cfg["output_tokens_bounds"]["max"])
    value = int(round(expected))
    return max(lower, min(upper, value))


def build_raw_usage_events_daily(
    pair_month_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for pair_month_row in pair_month_df.itertuples(index=False):
        row_dict = pair_month_row._asdict()
        row_series = pd.Series(row_dict)

        selected_dates = _select_active_dates_for_pair_month(
            row=row_series,
            config=config,
        )

        for usage_date in selected_dates:
            session_count = _realize_session_count(row_series, usage_date, config)
            prompt_count = _realize_prompt_count(
                row_series,
                usage_date,
                session_count,
                config,
            )
            input_tokens_total = _realize_input_tokens_total(
                row_series,
                usage_date,
                session_count,
                prompt_count,
                config,
            )
            output_tokens_total = _realize_output_tokens_total(
                row_series,
                usage_date,
                session_count,
                prompt_count,
                config,
            )

            rows.append(
                {
                    "usage_date": usage_date,
                    "user_id": str(row_series["user_id"]),
                    "tool_code": str(row_series["tool_code"]),
                    "session_count": int(session_count),
                    "prompt_count": int(prompt_count),
                    "input_tokens_total": int(input_tokens_total),
                    "output_tokens_total": int(output_tokens_total),
                }
            )

    usage_df = pd.DataFrame(rows)
    if usage_df.empty:
        raise ValidationError("produced an empty raw_usage_events_daily table.")

    usage_df = usage_df.sort_values(
        by=["usage_date", "user_id", "tool_code"],
        kind="stable",
    ).reset_index(drop=True)

    usage_columns = [
        "usage_date",
        "user_id",
        "tool_code",
        "session_count",
        "prompt_count",
        "input_tokens_total",
        "output_tokens_total",
    ]
    usage_df = usage_df.loc[:, usage_columns].copy()

    return usage_df
