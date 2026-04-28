from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

UTC = timezone.utc


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def month_end(value: date) -> date:
    start = month_start(value)
    last_day = monthrange(start.year, start.month)[1]
    return date(start.year, start.month, last_day)


def add_months(anchor: date, offset: int) -> date:
    anchor = month_start(anchor)
    month_index = (anchor.year * 12 + (anchor.month - 1)) + offset
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


def month_sequence(anchor_month: date, n_months: int) -> list[date]:
    if n_months < 1:
        raise ValueError("n_months must be >= 1.")

    anchor_month = month_start(anchor_month)
    oldest_offset = -(n_months - 1)
    return [add_months(anchor_month, offset) for offset in range(oldest_offset, 1)]


def month_difference(start_month: date, end_month: date) -> int:
    start_month = month_start(start_month)
    end_month = month_start(end_month)
    return (end_month.year - start_month.year) * 12 + (
        end_month.month - start_month.month
    )


def iter_dates_in_month(month: date) -> list[date]:
    month = month_start(month)
    last_day = monthrange(month.year, month.month)[1]
    return [date(month.year, month.month, day) for day in range(1, last_day + 1)]


def month_position_bucket(value: date) -> str:
    day = value.day
    last_day = monthrange(value.year, value.month)[1]

    if day <= 7:
        return "days_01_07"
    if day <= 14:
        return "days_08_14"
    if day <= 21:
        return "days_15_21"
    if day == last_day:
        return "final_calendar_day"
    return "days_22_to_month_end_minus_1"


def weekday_name(value: date) -> str:
    return value.strftime("%A").lower()


def build_utc_datetime(
    value_date: date,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> datetime:
    if not 0 <= hour <= 23:
        raise ValueError("hour must be in [0, 23].")
    if not 0 <= minute <= 59:
        raise ValueError("minute must be in [0, 59].")
    if not 0 <= second <= 59:
        raise ValueError("second must be in [0, 59].")

    return datetime(
        value_date.year,
        value_date.month,
        value_date.day,
        hour,
        minute,
        second,
        tzinfo=UTC,
    )


def is_timestamp_in_month(value: datetime, month: date) -> bool:
    month = month_start(month)
    value_utc = value.astimezone(UTC)
    return value_utc.year == month.year and value_utc.month == month.month


def month_end_timestamp_utc(month: date, epsilon_seconds: int = 1) -> datetime:
    if epsilon_seconds < 0:
        raise ValueError("epsilon_seconds must be >= 0.")

    next_month = add_months(month_start(month), 1)
    return build_utc_datetime(next_month, 0, 0, 0) - timedelta(seconds=epsilon_seconds)
