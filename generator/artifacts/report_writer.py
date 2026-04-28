from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from generator.types import OutputPaths


def _render_check_lines(results: Sequence[Mapping[str, Any]]) -> list[str]:
    lines: list[str] = []
    for result in results:
        status = "PASS" if bool(result["passed"]) else "FAIL"
        name = str(result["name"])
        details = str(result.get("details", ""))
        lines.append(f"- **{status}** `{name}` — {details}")
    return lines


def render_validation_summary_markdown(summary: Mapping[str, Any]) -> str:
    lines: list[str] = [
        "# Generator Validation Summary",
        "",
        "## Run Context",
        "",
        f"- Spec version: `{summary['spec_version']}`",
        f"- Seed: `{summary['seed']}`",
        f"- Anchor month: `{summary['anchor_month']}`",
        f"- Window months: `{summary['window_months']}`",
        f"- Dry run: `{summary['dry_run']}`",
        f"- All checks passed: `{summary['all_checks_passed']}`",
        f"- Check count: `{summary['check_count']}`",
        "",
        "## Raw Row Counts",
        "",
    ]

    raw_row_counts = summary["raw_row_counts"]
    for table_name, row_count in raw_row_counts.items():
        lines.append(f"- `{table_name}`: `{row_count}`")

    lines.extend(
        [
            "",
            "## Raw Output Paths",
            "",
        ]
    )
    for name, path in summary["raw_output_paths"].items():
        lines.append(f"- `{name}`: `{path}`")

    lines.extend(
        [
            "",
            "## Validation Output Paths",
            "",
        ]
    )
    for name, path in summary["validation_output_paths"].items():
        lines.append(f"- `{name}`: `{path}`")

    checks = summary["checks"]

    lines.extend(
        [
            "",
            "## Table-local QA",
            "",
        ]
    )
    lines.extend(_render_check_lines(checks["table_local"]))

    lines.extend(
        [
            "",
            "## Cross-table QA",
            "",
        ]
    )
    lines.extend(_render_check_lines(checks["cross_table"]))

    lines.extend(
        [
            "",
            "## Schema Realization QA (Pre-write)",
            "",
        ]
    )
    lines.extend(_render_check_lines(checks["schema_prewrite"]))

    if checks["schema_postwrite"]:
        lines.extend(
            [
                "",
                "## Schema Realization QA (Post-write)",
                "",
            ]
        )
        lines.extend(_render_check_lines(checks["schema_postwrite"]))

    lines.append("")
    return "\n".join(lines)


def write_validation_artifacts(
    *,
    summary: Mapping[str, Any],
    output_paths: OutputPaths,
) -> None:
    output_paths.validation.root.mkdir(parents=True, exist_ok=True)

    markdown_text = render_validation_summary_markdown(summary)
    output_paths.validation.summary_markdown.write_text(
        markdown_text,
        encoding="utf-8",
    )
    output_paths.validation.summary_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
