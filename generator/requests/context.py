from __future__ import annotations

import pandas as pd

from generator.helpers.deterministic import (
    deterministic_weighted_choice,
    make_deterministic_int,
)
from generator.types import RuntimeConfig, ToolSeed


def _submission_config(config: RuntimeConfig) -> dict:
    return dict(config.request_submission_config)


def assign_request_purpose(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    submission_config = _submission_config(config)
    purpose_values = tuple(submission_config["purpose_values"])
    team_purpose_base_weights = submission_config["team_purpose_base_weights"]
    tool_purpose_multipliers = submission_config["tool_purpose_multipliers"]

    request_purposes: list[str] = []

    for row in request_df.itertuples(index=False):
        weights = [
            float(team_purpose_base_weights[row.team_name][purpose])
            * float(tool_purpose_multipliers[row.tool_code][purpose])
            for purpose in purpose_values
        ]
        request_purposes.append(
            deterministic_weighted_choice(
                purpose_values,
                weights,
                row.request_id,
                row.team_name,
                row.tool_code,
                seed=config.seed,
                namespace="request_purpose_choice",
            )
        )

    enriched_df = request_df.copy()
    enriched_df["request_purpose"] = request_purposes
    return enriched_df


def assign_data_classification(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    submission_config = _submission_config(config)
    classification_values = tuple(submission_config["classification_values"])
    purpose_classification_base_weights = submission_config[
        "purpose_classification_base_weights"
    ]
    team_classification_multipliers = submission_config[
        "team_classification_multipliers"
    ]

    classifications: list[str] = []

    for row in request_df.itertuples(index=False):
        weights = [
            float(
                purpose_classification_base_weights[row.request_purpose][classification]
            )
            * float(team_classification_multipliers[row.team_name][classification])
            for classification in classification_values
        ]
        classifications.append(
            deterministic_weighted_choice(
                classification_values,
                weights,
                row.request_id,
                row.team_name,
                row.request_purpose,
                seed=config.seed,
                namespace="data_classification_choice",
            )
        )

    enriched_df = request_df.copy()
    enriched_df["data_classification"] = classifications
    return enriched_df


def _select_clause(
    request_id: str,
    bucket_name: str,
    clauses: list[str],
    config: RuntimeConfig,
) -> str:
    clause_index = make_deterministic_int(
        request_id,
        bucket_name,
        low=0,
        high=len(clauses) - 1,
        seed=config.seed,
        namespace="business_justification_clause_index",
    )
    return clauses[clause_index]


def generate_business_justification_text(
    request_df: pd.DataFrame,
    tool_seed: ToolSeed,
    config: RuntimeConfig,
) -> pd.DataFrame:
    submission_config = _submission_config(config)
    text_config = submission_config["business_justification_text"]

    tool_lookup = {
        tool.tool_code: {
            "tool_name": tool.tool_name,
            "tool_category": tool.tool_category,
        }
        for tool in tool_seed.tools
    }

    business_texts: list[str] = []

    for row in request_df.itertuples(index=False):
        tool_meta = tool_lookup[row.tool_code]
        tool_name = str(tool_meta["tool_name"])
        tool_category = str(tool_meta["tool_category"])

        purpose_clause = _select_clause(
            row.request_id,
            "purpose",
            list(text_config["purpose_clauses"][row.request_purpose]),
            config,
        )
        tool_clause = _select_clause(
            row.request_id,
            "tool_fit",
            list(text_config["tool_fit_clauses"][tool_category]),
            config,
        ).format(tool_name=tool_name)
        data_clause = _select_clause(
            row.request_id,
            "data",
            list(text_config["data_clauses"][row.data_classification]),
            config,
        )
        control_clause = _select_clause(
            row.request_id,
            "control",
            list(text_config["control_clauses"][row.data_classification]),
            config,
        )

        separator = " " if bool(text_config["join_with_space"]) else ""
        business_texts.append(
            separator.join(
                [
                    purpose_clause.strip(),
                    tool_clause.strip(),
                    data_clause.strip(),
                    control_clause.strip(),
                ]
            ).strip()
        )

    enriched_df = request_df.copy()
    enriched_df["business_justification_text"] = business_texts
    return enriched_df
