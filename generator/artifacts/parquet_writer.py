from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from generator.types import OutputPaths


def write_raw_parquet_outputs(
    *,
    raw_tables: Mapping[str, pd.DataFrame],
    output_paths: OutputPaths,
) -> None:
    raw_path_lookup = {name: path for name, path in output_paths.raw.named_items()}

    missing_paths = sorted(set(raw_tables.keys()) - set(raw_path_lookup.keys()))
    if missing_paths:
        raise ValueError(
            f"Missing canonical raw output paths for tables: {missing_paths}"
        )

    for table_name, df in raw_tables.items():
        raw_path_lookup[table_name].parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(raw_path_lookup[table_name], index=False)
