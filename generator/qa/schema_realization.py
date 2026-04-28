from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from generator.helpers.validation import ValidationError
from generator.types import OutputPaths

EXPECTED_RAW_TABLE_NAMES = (
    "raw_tool_catalog",
    "raw_user_directory",
    "raw_access_requests",
    "raw_usage_events_daily",
    "raw_tool_spend_monthly",
)


def _passed(name: str, details: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": True,
        "details": details,
    }


def run_schema_realization_prewrite_qa(
    *,
    raw_tables: Mapping[str, pd.DataFrame],
    output_paths: OutputPaths,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    actual_names = tuple(raw_tables.keys())
    if actual_names != EXPECTED_RAW_TABLE_NAMES:
        raise ValidationError(
            "Final raw-table bundle must contain the canonical table set in canonical order; "
            f"expected={EXPECTED_RAW_TABLE_NAMES}, got={actual_names}."
        )

    for table_name in EXPECTED_RAW_TABLE_NAMES:
        if not isinstance(raw_tables[table_name], pd.DataFrame):
            raise ValidationError(
                f"{table_name} must be realized as a pandas DataFrame before write."
            )

    raw_path_names = tuple(name for name, _ in output_paths.raw.named_items())
    if raw_path_names != EXPECTED_RAW_TABLE_NAMES:
        raise ValidationError(
            "Raw output path contract must preserve canonical table-path naming."
        )

    raw_paths = [path for _, path in output_paths.raw.named_items()]
    if len(set(raw_paths)) != len(raw_paths):
        raise ValidationError("Raw output paths must be unique.")

    validation_paths = [path for _, path in output_paths.validation.named_items()]
    if len(set(validation_paths)) != len(validation_paths):
        raise ValidationError("Validation artifact paths must be unique.")

    results.append(
        _passed(
            "raw_table_bundle_contract",
            "Five canonical raw tables are present in memory with canonical naming.",
        )
    )
    results.append(
        _passed(
            "output_path_contract",
            "Canonical raw-output and validation-artifact paths are configured.",
        )
    )

    return results


def run_schema_realization_postwrite_qa(
    *,
    output_paths: OutputPaths,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    missing_raw_files = [
        name
        for name, path in output_paths.raw.named_items()
        if not path.exists() or not path.is_file()
    ]
    if missing_raw_files:
        raise ValidationError(
            f"Some raw parquet outputs were not written: {missing_raw_files}"
        )

    empty_raw_files = [
        name
        for name, path in output_paths.raw.named_items()
        if path.stat().st_size == 0
    ]
    if empty_raw_files:
        raise ValidationError(
            f"Some raw parquet outputs are empty files: {empty_raw_files}"
        )

    missing_validation_files = [
        name
        for name, path in output_paths.validation.named_items()
        if not path.exists() or not path.is_file()
    ]
    if missing_validation_files:
        raise ValidationError(
            f"Some validation artifacts were not written: {missing_validation_files}"
        )

    empty_validation_files = [
        name
        for name, path in output_paths.validation.named_items()
        if path.stat().st_size == 0
    ]
    if empty_validation_files:
        raise ValidationError(
            f"Some validation artifacts are empty files: {empty_validation_files}"
        )

    results.append(
        _passed(
            "raw_parquet_files_written",
            "All canonical raw parquet outputs exist on disk and are non-empty.",
        )
    )
    results.append(
        _passed(
            "validation_artifacts_written",
            "All canonical validation artifacts exist on disk and are non-empty.",
        )
    )

    return results
