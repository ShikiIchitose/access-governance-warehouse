"""Load local raw Parquet fixtures into BigQuery raw tables.

This script loads the five deterministic raw Parquet files used by the
access-governance warehouse project into the BigQuery raw dataset.

Authentication is expected to use Application Default Credentials.

Example:
    export GCP_PROJECT_ID="your-gcp-project-id"

    uv run python scripts/load_raw_to_bigquery.py \
      --project-id "${GCP_PROJECT_ID}" \
      --location asia-northeast1
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from google.api_core.exceptions import GoogleAPIError, NotFound
from google.cloud import bigquery

DEFAULT_DATASET_ID = "access_governance_raw"
DEFAULT_LOCATION = "asia-northeast1"

RAW_TABLE_SPECS: tuple[RawTableSpec, ...]  # forward declaration for type checkers


@dataclass(frozen=True)
class RawTableSpec:
    """Mapping from a local Parquet file to a BigQuery raw table."""

    table_id: str
    parquet_filename: str


@dataclass(frozen=True)
class LoadResult:
    """Result metadata for one loaded BigQuery table."""

    table_id: str
    source_path: Path
    destination: str
    output_rows: int | None
    table_num_rows: int
    table_num_bytes: int


RAW_TABLE_SPECS = (
    RawTableSpec(
        table_id="raw_tool_catalog",
        parquet_filename="raw_tool_catalog.parquet",
    ),
    RawTableSpec(
        table_id="raw_user_directory",
        parquet_filename="raw_user_directory.parquet",
    ),
    RawTableSpec(
        table_id="raw_access_requests",
        parquet_filename="raw_access_requests.parquet",
    ),
    RawTableSpec(
        table_id="raw_usage_events_daily",
        parquet_filename="raw_usage_events_daily.parquet",
    ),
    RawTableSpec(
        table_id="raw_tool_spend_monthly",
        parquet_filename="raw_tool_spend_monthly.parquet",
    ),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Load local raw Parquet fixtures into BigQuery raw tables.",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GCP_PROJECT_ID"),
        help=(
            "Google Cloud project ID. "
            "Defaults to the GCP_PROJECT_ID environment variable."
        ),
    )
    parser.add_argument(
        "--dataset-id",
        default=DEFAULT_DATASET_ID,
        help=f"BigQuery raw dataset ID. Default: {DEFAULT_DATASET_ID}",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("BQ_LOCATION", DEFAULT_LOCATION),
        help=f"BigQuery job location. Default: {DEFAULT_LOCATION}",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing raw Parquet files. Default: data/raw",
    )
    parser.add_argument(
        "--write-disposition",
        choices=(
            bigquery.WriteDisposition.WRITE_TRUNCATE,
            bigquery.WriteDisposition.WRITE_APPEND,
            bigquery.WriteDisposition.WRITE_EMPTY,
        ),
        default=bigquery.WriteDisposition.WRITE_TRUNCATE,
        help="BigQuery write disposition. Default: WRITE_TRUNCATE",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate local inputs and print the load plan without loading data.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Timeout for each BigQuery load job. Default: 300",
    )

    args = parser.parse_args(argv)

    if not args.project_id:
        parser.error("--project-id is required unless GCP_PROJECT_ID is set.")

    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be a positive integer.")

    return args


def resolve_project_root() -> Path:
    """Return the repository root inferred from this script location."""

    return Path(__file__).resolve().parents[1]


def resolve_raw_dir(project_root: Path, raw_dir: Path) -> Path:
    """Resolve raw directory relative to project root when needed."""

    if raw_dir.is_absolute():
        return raw_dir
    return project_root / raw_dir


def validate_raw_files(raw_dir: Path) -> dict[str, Path]:
    """Validate that all expected raw Parquet files exist and are non-empty."""

    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw directory does not exist: {raw_dir}")

    if not raw_dir.is_dir():
        raise NotADirectoryError(f"Raw path is not a directory: {raw_dir}")

    paths: dict[str, Path] = {}

    for spec in RAW_TABLE_SPECS:
        source_path = raw_dir / spec.parquet_filename

        if not source_path.exists():
            raise FileNotFoundError(f"Missing raw Parquet file: {source_path}")

        if not source_path.is_file():
            raise FileNotFoundError(f"Raw path is not a file: {source_path}")

        if source_path.stat().st_size == 0:
            raise ValueError(f"Raw Parquet file is empty: {source_path}")

        paths[spec.table_id] = source_path

    return paths


def format_table_ref(project_id: str, dataset_id: str, table_id: str) -> str:
    """Return a BigQuery table reference string accepted by the Python client."""

    return f"{project_id}.{dataset_id}.{table_id}"


def ensure_dataset_exists(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
) -> None:
    """Fail early if the target BigQuery dataset does not exist."""

    dataset_ref = f"{project_id}.{dataset_id}"

    try:
        client.get_dataset(dataset_ref)
    except NotFound as exc:
        raise RuntimeError(
            f"BigQuery dataset was not found. Create it first: {dataset_ref}"
        ) from exc


def load_one_table(
    client: bigquery.Client,
    *,
    project_id: str,
    dataset_id: str,
    spec: RawTableSpec,
    source_path: Path,
    write_disposition: str,
    timeout_seconds: int,
) -> LoadResult:
    """Load one local Parquet file into one BigQuery table."""

    destination = format_table_ref(
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=spec.table_id,
    )

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=write_disposition,
    )

    with source_path.open("rb") as source_file:
        load_job = client.load_table_from_file(
            source_file,
            destination=destination,
            job_config=job_config,
            location=client.location,
        )

    load_job.result(timeout=timeout_seconds)

    loaded_table = client.get_table(destination)

    if loaded_table.num_rows is None:
        raise RuntimeError(f"BigQuery table row count was not available: {destination}")

    if loaded_table.num_bytes is None:
        raise RuntimeError(f"BigQuery table byte size was not available: {destination}")

    return LoadResult(
        table_id=spec.table_id,
        source_path=source_path,
        destination=destination,
        output_rows=load_job.output_rows,
        table_num_rows=loaded_table.num_rows,
        table_num_bytes=loaded_table.num_bytes,
    )


def print_plan(
    *,
    project_id: str,
    dataset_id: str,
    location: str,
    raw_paths: dict[str, Path],
    write_disposition: str,
) -> None:
    """Print the load plan."""

    print("BigQuery raw load plan")
    print(f"  project_id: {project_id}")
    print(f"  dataset_id: {dataset_id}")
    print(f"  location: {location}")
    print(f"  write_disposition: {write_disposition}")
    print()

    for spec in RAW_TABLE_SPECS:
        source_path = raw_paths[spec.table_id]
        destination = format_table_ref(
            project_id=project_id,
            dataset_id=dataset_id,
            table_id=spec.table_id,
        )
        print(f"  {source_path} -> {destination}")


def print_results(results: Sequence[LoadResult]) -> None:
    """Print load results in a compact table."""

    print()
    print("Loaded BigQuery raw tables")
    print("| table_id | output_rows | table_num_rows | table_num_bytes |")
    print("|---|---:|---:|---:|")

    for result in results:
        output_rows = (
            str(result.output_rows) if result.output_rows is not None else "unknown"
        )
        print(
            f"| {result.table_id} "
            f"| {output_rows} "
            f"| {result.table_num_rows} "
            f"| {result.table_num_bytes} |"
        )


def run(args: argparse.Namespace) -> int:
    """Run the raw Parquet loading workflow."""

    project_root = resolve_project_root()
    raw_dir = resolve_raw_dir(project_root=project_root, raw_dir=args.raw_dir)
    raw_paths = validate_raw_files(raw_dir)

    print_plan(
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        location=args.location,
        raw_paths=raw_paths,
        write_disposition=args.write_disposition,
    )

    if args.dry_run:
        print()
        print("Dry run completed. No BigQuery load jobs were submitted.")
        return 0

    client = bigquery.Client(
        project=args.project_id,
        location=args.location,
    )

    ensure_dataset_exists(
        client=client,
        project_id=args.project_id,
        dataset_id=args.dataset_id,
    )

    results: list[LoadResult] = []

    for spec in RAW_TABLE_SPECS:
        result = load_one_table(
            client=client,
            project_id=args.project_id,
            dataset_id=args.dataset_id,
            spec=spec,
            source_path=raw_paths[spec.table_id],
            write_disposition=args.write_disposition,
            timeout_seconds=args.timeout_seconds,
        )
        results.append(result)

    print_results(results)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""

    args = parse_args(argv)

    try:
        return run(args)
    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except GoogleAPIError as exc:
        print(f"ERROR: BigQuery API error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
