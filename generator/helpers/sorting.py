from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd


def build_order_lookup(values: Sequence[str]) -> dict[str, int]:
    lookup: dict[str, int] = {}
    duplicates: list[str] = []

    for index, value in enumerate(values):
        if value in lookup:
            duplicates.append(value)
        else:
            lookup[value] = index

    if duplicates:
        raise ValueError(
            f"values must be unique to build an order lookup: {duplicates}"
        )

    return lookup


def categorical_order_key(
    series: pd.Series,
    order_lookup: Mapping[str, int],
    *,
    on_missing: str = "raise",
) -> pd.Series:
    mapped = series.map(order_lookup)

    if mapped.isna().any():
        missing_values = sorted({str(value) for value in series[mapped.isna()]})
        if on_missing == "raise":
            raise KeyError(f"values missing from order_lookup: {missing_values}")
        if on_missing == "last":
            fill_value = len(order_lookup)
            mapped = mapped.fillna(fill_value)
        else:
            raise ValueError("on_missing must be either 'raise' or 'last'.")

    return mapped.astype("int64")


def _normalize_ascending(
    by: Sequence[str],
    ascending: bool | Sequence[bool],
) -> list[bool]:
    if isinstance(ascending, bool):
        return [ascending] * len(by)

    ascending_list = list(ascending)
    if len(ascending_list) != len(by):
        raise ValueError("len(ascending) must match len(by).")
    return ascending_list


def stable_sort(
    df: pd.DataFrame,
    by: Sequence[str],
    *,
    ascending: bool | Sequence[bool] = True,
    ignore_index: bool = True,
) -> pd.DataFrame:
    columns = list(by)
    if not columns:
        return df.reset_index(drop=True) if ignore_index else df.copy()

    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        raise KeyError(f"stable_sort columns not found in DataFrame: {missing_columns}")

    ascending_list = _normalize_ascending(columns, ascending)
    result = df.copy()

    for column, is_ascending in reversed(list(zip(columns, ascending_list))):
        result = result.sort_values(
            by=column,
            ascending=is_ascending,
            kind="stable",
            na_position="last",
            ignore_index=False,
        )

    if ignore_index:
        result = result.reset_index(drop=True)

    return result


def stable_sort_with_order_lookups(
    df: pd.DataFrame,
    by: Sequence[str],
    *,
    order_lookups: Mapping[str, Mapping[str, int]] | None = None,
    ascending: bool | Sequence[bool] = True,
    ignore_index: bool = True,
) -> pd.DataFrame:
    if order_lookups is None:
        return stable_sort(
            df,
            by=by,
            ascending=ascending,
            ignore_index=ignore_index,
        )

    result = df.copy()
    temp_columns: list[str] = []
    resolved_sort_columns: list[str] = []

    for column in by:
        if column in order_lookups:
            temp_column = f"__order_{column}"
            result[temp_column] = categorical_order_key(
                result[column],
                order_lookups[column],
                on_missing="raise",
            )
            temp_columns.append(temp_column)
            resolved_sort_columns.append(temp_column)
        else:
            resolved_sort_columns.append(column)

    result = stable_sort(
        result,
        by=resolved_sort_columns,
        ascending=ascending,
        ignore_index=ignore_index,
    )

    if temp_columns:
        result = result.drop(columns=temp_columns)

    return result
