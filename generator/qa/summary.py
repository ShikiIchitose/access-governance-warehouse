from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from generator.types import OutputPaths, RuntimeConfig


def _normalize_results(
    results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "name": str(result["name"]),
            "passed": bool(result.get("passed", False)),
            "details": str(result.get("details", "")),
        }
        for result in results
    ]


def build_validation_summary(
    *,
    raw_tables: Mapping[str, pd.DataFrame],
    table_local_results: Sequence[Mapping[str, Any]],
    cross_table_results: Sequence[Mapping[str, Any]],
    schema_prewrite_results: Sequence[Mapping[str, Any]],
    config: RuntimeConfig,
    output_paths: OutputPaths,
    dry_run: bool,
    schema_postwrite_results: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    checks = {
        "table_local": _normalize_results(table_local_results),
        "cross_table": _normalize_results(cross_table_results),
        "schema_prewrite": _normalize_results(schema_prewrite_results),
        "schema_postwrite": _normalize_results(schema_postwrite_results or []),
    }

    flat_results = [result for results in checks.values() for result in results]

    return {
        "spec_version": config.spec_version,
        "seed": int(config.seed),
        "anchor_month": config.anchor_month.isoformat(),
        "window_months": int(config.n_months),
        "dry_run": bool(dry_run),
        "all_checks_passed": all(result["passed"] for result in flat_results),
        "check_count": len(flat_results),
        "raw_row_counts": {
            table_name: int(len(df)) for table_name, df in raw_tables.items()
        },
        "raw_targets": {key: int(value) for key, value in config.raw_targets.items()},
        "raw_target_ranges": {
            key: [int(value[0]), int(value[1])]
            for key, value in config.raw_target_ranges.items()
        },
        "raw_output_paths": {
            name: str(path) for name, path in output_paths.raw.named_items()
        },
        "validation_output_paths": {
            name: str(path) for name, path in output_paths.validation.named_items()
        },
        "checks": checks,
    }
