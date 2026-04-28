from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

import pandas as pd

from generator.helpers.dates import (
    build_utc_datetime,
    iter_dates_in_month,
    month_position_bucket,
    weekday_name,
)
from generator.helpers.deterministic import (
    deterministic_weighted_choice,
    make_deterministic_int,
    make_deterministic_jitter,
)
from generator.types import RuntimeConfig


def _requested_at_config(config: RuntimeConfig) -> dict:
    return dict(config.request_submission_config["requested_at"])


def _review_lag_config(config: RuntimeConfig) -> dict:
    return dict(config.request_review_config["review_lag"])


def _tool_risk_lookup(config: RuntimeConfig) -> dict[str, str]:
    return {
        str(tool["tool_code"]): str(tool["risk_tier"]) for tool in config.tool_config
    }


def _coerce_datetime(value: object) -> datetime:
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    raise TypeError(f"Expected datetime-like value, got {type(value)!r}.")


def _last_calendar_day_of_month(month: date) -> date:
    last_day = calendar.monthrange(month.year, month.month)[1]
    return date(month.year, month.month, last_day)


def _month_end_datetime(month: date) -> datetime:
    last_day = _last_calendar_day_of_month(month)
    return build_utc_datetime(last_day, 23, 59, 59)


def _select_request_date(
    request_month: date,
    request_id: str,
    requester_user_id: str,
    config: RuntimeConfig,
) -> date:
    requested_at_config = _requested_at_config(config)
    weekday_weights = requested_at_config["weekday_weights"]
    bucket_weights = requested_at_config["month_position_bucket_weights"]
    low, high = requested_at_config["date_jitter_range"]

    candidate_dates = iter_dates_in_month(request_month)
    candidate_weights: list[float] = []

    for candidate_date in candidate_dates:
        weight = (
            float(weekday_weights[weekday_name(candidate_date)])
            * float(bucket_weights[month_position_bucket(candidate_date)])
            * make_deterministic_jitter(
                request_id,
                requester_user_id,
                candidate_date,
                low=low,
                high=high,
                seed=config.seed,
                namespace="requested_at_date_jitter",
            )
        )
        candidate_weights.append(weight)

    return deterministic_weighted_choice(
        candidate_dates,
        candidate_weights,
        request_id,
        requester_user_id,
        request_month,
        seed=config.seed,
        namespace="requested_at_date_choice",
    )


def _select_request_hour(
    request_date: date,
    request_id: str,
    requester_user_id: str,
    config: RuntimeConfig,
) -> int:
    requested_at_config = _requested_at_config(config)
    hour_weights = requested_at_config["request_hour_weights_utc"]
    low, high = requested_at_config["hour_jitter_range"]

    candidate_hours = tuple(sorted(int(hour) for hour in hour_weights.keys()))
    candidate_weights: list[float] = []

    for hour in candidate_hours:
        weight = float(hour_weights[hour]) * make_deterministic_jitter(
            request_id,
            requester_user_id,
            request_date,
            hour,
            low=low,
            high=high,
            seed=config.seed,
            namespace="requested_at_hour_jitter",
        )
        candidate_weights.append(weight)

    return int(
        deterministic_weighted_choice(
            candidate_hours,
            candidate_weights,
            request_id,
            requester_user_id,
            request_date,
            seed=config.seed,
            namespace="requested_at_hour_choice",
        )
    )


def _select_minute_and_second(
    request_id: str,
    requester_user_id: str,
    request_date: date,
    request_hour: int,
    config: RuntimeConfig,
) -> tuple[int, int]:
    requested_at_config = _requested_at_config(config)

    minute_low, minute_high = requested_at_config["minute_range"]
    second_low, second_high = requested_at_config["second_range"]

    minute = make_deterministic_int(
        request_id,
        requester_user_id,
        request_date,
        request_hour,
        "minute",
        low=int(minute_low),
        high=int(minute_high),
        seed=config.seed,
        namespace="requested_at_minute",
    )
    second = make_deterministic_int(
        request_id,
        requester_user_id,
        request_date,
        request_hour,
        "second",
        low=int(second_low),
        high=int(second_high),
        seed=config.seed,
        namespace="requested_at_second",
    )
    return minute, second


def assign_requested_at(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    requested_at_values: list[datetime] = []

    for row in request_df.itertuples(index=False):
        request_date = _select_request_date(
            row.request_month,
            row.request_id,
            row.requester_user_id,
            config,
        )
        request_hour = _select_request_hour(
            request_date,
            row.request_id,
            row.requester_user_id,
            config,
        )
        minute, second = _select_minute_and_second(
            row.request_id,
            row.requester_user_id,
            request_date,
            request_hour,
            config,
        )
        requested_at_values.append(
            build_utc_datetime(request_date, request_hour, minute, second)
        )

    enriched_df = request_df.copy()
    enriched_df["requested_at"] = pd.to_datetime(requested_at_values, utc=True)
    return enriched_df


def _select_review_hour(
    *,
    request_id: str,
    request_status: str,
    candidate_date: date,
    lag_mode: str,
    hour_weights: dict[int, float],
    config: RuntimeConfig,
) -> int:
    candidate_hours = tuple(sorted(int(hour) for hour in hour_weights.keys()))
    candidate_weights = [float(hour_weights[hour]) for hour in candidate_hours]

    return int(
        deterministic_weighted_choice(
            candidate_hours,
            candidate_weights,
            request_id,
            request_status,
            candidate_date,
            lag_mode,
            seed=config.seed,
            namespace=f"reviewed_at_{lag_mode}_hour_choice",
        )
    )


def _select_review_minute_and_second(
    *,
    request_id: str,
    request_status: str,
    candidate_date: date,
    review_hour: int,
    lag_mode: str,
    minute_range: tuple[int, int],
    second_range: tuple[int, int],
    config: RuntimeConfig,
) -> tuple[int, int]:
    minute_low, minute_high = minute_range
    second_low, second_high = second_range

    minute = make_deterministic_int(
        request_id,
        request_status,
        candidate_date,
        review_hour,
        lag_mode,
        "minute",
        low=int(minute_low),
        high=int(minute_high),
        seed=config.seed,
        namespace=f"reviewed_at_{lag_mode}_minute",
    )
    second = make_deterministic_int(
        request_id,
        request_status,
        candidate_date,
        review_hour,
        lag_mode,
        "second",
        low=int(second_low),
        high=int(second_high),
        seed=config.seed,
        namespace=f"reviewed_at_{lag_mode}_second",
    )
    return int(minute), int(second)


def _build_review_business_datetime(
    *,
    request_id: str,
    request_status: str,
    candidate_date: date,
    lag_mode: str,
    hour_weights: dict[int, float],
    minute_range: tuple[int, int],
    second_range: tuple[int, int],
    config: RuntimeConfig,
) -> datetime:
    review_hour = _select_review_hour(
        request_id=request_id,
        request_status=request_status,
        candidate_date=candidate_date,
        lag_mode=lag_mode,
        hour_weights=hour_weights,
        config=config,
    )
    review_minute, review_second = _select_review_minute_and_second(
        request_id=request_id,
        request_status=request_status,
        candidate_date=candidate_date,
        review_hour=review_hour,
        lag_mode=lag_mode,
        minute_range=minute_range,
        second_range=second_range,
        config=config,
    )
    return build_utc_datetime(
        candidate_date,
        review_hour,
        review_minute,
        review_second,
    )


def _build_next_valid_business_reviewed_at(
    *,
    request_id: str,
    request_status: str,
    start_date: date,
    lower_bound: datetime,
    upper_bound: datetime,
    lag_mode: str,
    hour_weights: dict[int, float],
    minute_range: tuple[int, int],
    second_range: tuple[int, int],
    config: RuntimeConfig,
) -> datetime:
    current_date = start_date
    upper_date = upper_bound.date()

    while current_date <= upper_date:
        candidate = _build_review_business_datetime(
            request_id=request_id,
            request_status=request_status,
            candidate_date=current_date,
            lag_mode=lag_mode,
            hour_weights=hour_weights,
            minute_range=minute_range,
            second_range=second_range,
            config=config,
        )
        if lower_bound < candidate <= upper_bound:
            return candidate
        current_date += timedelta(days=1)

    return upper_bound


def _build_same_month_reviewed_at(
    *,
    request_id: str,
    requested_at: datetime,
    review_month: date,
    request_status: str,
    data_classification: str,
    risk_tier: str,
    config: RuntimeConfig,
) -> datetime:
    lag_config = _review_lag_config(config)["same_month"]

    base_hours = int(lag_config["base_lag_hours_by_status"][request_status])
    classification_adjustment = int(
        lag_config["classification_hour_adjustment"][data_classification]
    )
    risk_adjustment = int(lag_config["risk_tier_hour_adjustment"][risk_tier])
    jitter_low, jitter_high = lag_config["jitter_hours_range"]
    jitter_hours = int(
        round(
            make_deterministic_jitter(
                request_id,
                request_status,
                data_classification,
                risk_tier,
                low=float(jitter_low),
                high=float(jitter_high),
                seed=config.seed,
                namespace="reviewed_at_same_month_jitter_hours",
            )
        )
    )

    lag_hours = base_hours + classification_adjustment + risk_adjustment + jitter_hours
    lag_hours = max(
        lag_hours, int(lag_config["min_lag_hours_by_status"][request_status])
    )
    lag_hours = min(
        lag_hours, int(lag_config["max_lag_hours_by_status"][request_status])
    )

    raw_candidate = requested_at + timedelta(hours=lag_hours)
    upper_bound = _month_end_datetime(review_month)

    hour_weights = {
        int(hour): float(weight)
        for hour, weight in lag_config["review_hour_weights_utc"].items()
    }
    minute_low, minute_high = lag_config["minute_range"]
    second_low, second_high = lag_config["second_range"]

    minute_range = (int(minute_low), int(minute_high))
    second_range = (int(second_low), int(second_high))

    start_date = raw_candidate.date()
    if start_date < review_month:
        start_date = review_month
    if start_date > upper_bound.date():
        start_date = upper_bound.date()

    candidate = _build_next_valid_business_reviewed_at(
        request_id=request_id,
        request_status=request_status,
        start_date=start_date,
        lower_bound=raw_candidate,
        upper_bound=upper_bound,
        lag_mode="same_month",
        hour_weights=hour_weights,
        minute_range=minute_range,
        second_range=second_range,
        config=config,
    )

    if candidate <= requested_at:
        candidate = upper_bound

    return candidate


def _build_carryover_reviewed_at(
    *,
    request_id: str,
    requested_at: datetime,
    review_month: date,
    request_status: str,
    data_classification: str,
    risk_tier: str,
    config: RuntimeConfig,
) -> datetime:
    lag_config = _review_lag_config(config)["carryover"]

    base_days = int(lag_config["base_day_offset_by_status"][request_status])
    classification_adjustment = int(
        lag_config["classification_day_adjustment"][data_classification]
    )
    risk_adjustment = int(lag_config["risk_tier_day_adjustment"][risk_tier])
    jitter_low, jitter_high = lag_config["jitter_days_range"]
    jitter_days = int(
        round(
            make_deterministic_jitter(
                request_id,
                request_status,
                data_classification,
                risk_tier,
                low=float(jitter_low),
                high=float(jitter_high),
                seed=config.seed,
                namespace="reviewed_at_carryover_jitter_days",
            )
        )
    )

    day_offset = base_days + classification_adjustment + risk_adjustment + jitter_days
    day_offset = max(day_offset, 0)
    day_offset = min(day_offset, int(lag_config["max_day_offset_in_review_month"]))

    candidate_date = review_month + timedelta(days=day_offset)
    last_day = _last_calendar_day_of_month(review_month)
    if candidate_date > last_day:
        candidate_date = last_day

    upper_bound = _month_end_datetime(review_month)

    hour_weights = {
        int(hour): float(weight)
        for hour, weight in lag_config["review_hour_weights_utc"].items()
    }
    minute_low, minute_high = lag_config["minute_range"]
    second_low, second_high = lag_config["second_range"]

    minute_range = (int(minute_low), int(minute_high))
    second_range = (int(second_low), int(second_high))

    candidate = _build_next_valid_business_reviewed_at(
        request_id=request_id,
        request_status=request_status,
        start_date=candidate_date,
        lower_bound=requested_at,
        upper_bound=upper_bound,
        lag_mode="carryover",
        hour_weights=hour_weights,
        minute_range=minute_range,
        second_range=second_range,
        config=config,
    )

    if candidate <= requested_at:
        candidate = upper_bound

    return candidate


def assign_reviewed_at(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    review_lag_config = _review_lag_config(config)
    null_statuses = set(review_lag_config["null_reviewed_at_for_statuses"])
    non_null_statuses = set(review_lag_config["non_null_reviewed_at_for_statuses"])
    risk_tier_by_tool = _tool_risk_lookup(config)

    reviewed_at_values: list[datetime | None] = []

    for row in request_df.itertuples(index=False):
        request_status = str(row.request_status)

        if request_status in null_statuses:
            reviewed_at_values.append(None)
            continue

        if request_status not in non_null_statuses:
            raise ValueError(
                f"Unexpected request_status for reviewed_at realization: {request_status!r}"
            )

        requested_at = _coerce_datetime(row.requested_at)
        review_month = row.review_month
        if review_month is None:
            raise ValueError(
                f"Reviewed row must have non-null review_month; request_id={row.request_id!r}."
            )

        risk_tier = risk_tier_by_tool[str(row.tool_code)]

        if int(row.review_month_index) == int(row.month_index):
            reviewed_at = _build_same_month_reviewed_at(
                request_id=str(row.request_id),
                requested_at=requested_at,
                review_month=review_month,
                request_status=request_status,
                data_classification=str(row.data_classification),
                risk_tier=risk_tier,
                config=config,
            )
        else:
            reviewed_at = _build_carryover_reviewed_at(
                request_id=str(row.request_id),
                requested_at=requested_at,
                review_month=review_month,
                request_status=request_status,
                data_classification=str(row.data_classification),
                risk_tier=risk_tier,
                config=config,
            )

        reviewed_at_values.append(reviewed_at)

    enriched_df = request_df.copy()
    enriched_df["reviewed_at"] = pd.to_datetime(reviewed_at_values, utc=True)
    return enriched_df
