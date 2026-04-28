from __future__ import annotations

from pathlib import Path

from generator.types import OutputPaths, RawOutputPaths, ValidationArtifactPaths


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_output_paths(repo_root: Path | None = None) -> OutputPaths:
    base = repo_root if repo_root is not None else get_repo_root()

    raw_root = base / "data" / "raw"
    validation_root = base / "artifacts" / "validation"

    raw = RawOutputPaths(
        root=raw_root,
        tool_catalog=raw_root / "raw_tool_catalog.parquet",
        user_directory=raw_root / "raw_user_directory.parquet",
        access_requests=raw_root / "raw_access_requests.parquet",
        usage_events_daily=raw_root / "raw_usage_events_daily.parquet",
        tool_spend_monthly=raw_root / "raw_tool_spend_monthly.parquet",
    )

    validation = ValidationArtifactPaths(
        root=validation_root,
        summary_markdown=validation_root / "generator_validation_summary.md",
        summary_json=validation_root / "generator_validation_summary.json",
    )

    return OutputPaths(
        repo_root=base,
        raw=raw,
        validation=validation,
    )


def ensure_output_directories(output_paths: OutputPaths) -> None:
    for directory in output_paths.all_directories():
        directory.mkdir(parents=True, exist_ok=True)
