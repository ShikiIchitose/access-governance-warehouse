from __future__ import annotations

from collections.abc import Mapping
from math import floor

from generator.config import GENERATOR_SEED
from generator.helpers.deterministic import make_hash_int


def normalize_weights(weight_map: Mapping[str, float]) -> dict[str, float]:
    if not weight_map:
        raise ValueError("weight_map must not be empty.")

    normalized_source = {key: float(value) for key, value in weight_map.items()}
    negative_keys = [key for key, value in normalized_source.items() if value < 0.0]
    if negative_keys:
        raise ValueError(
            f"weights must be non-negative; found negatives for keys: {negative_keys}"
        )

    total = sum(normalized_source.values())
    if total <= 0.0:
        raise ValueError("sum(weight_map.values()) must be > 0.")

    return {key: value / total for key, value in normalized_source.items()}


def largest_remainder_allocate(
    weights: Mapping[str, float],
    total: int,
    *,
    seed: int = GENERATOR_SEED,
    namespace: str = "largest_remainder",
) -> dict[str, int]:
    if not weights:
        raise ValueError("weights must not be empty.")
    if total < 0:
        raise ValueError("total must be >= 0.")

    if total == 0:
        return {key: 0 for key in weights}

    normalized = normalize_weights(weights)
    provisional = {key: normalized[key] * total for key in normalized}
    allocated = {key: int(floor(value)) for key, value in provisional.items()}

    remainder_slots = total - sum(allocated.values())
    if remainder_slots < 0:
        raise RuntimeError(
            "remainder_slots became negative; allocation logic is broken."
        )

    ranked_keys = sorted(
        normalized.keys(),
        key=lambda key: (
            -(provisional[key] - allocated[key]),
            make_hash_int(
                key,
                seed=seed,
                namespace=f"{namespace}:tie_break",
                digest_size=8,
            ),
            key,
        ),
    )

    for key in ranked_keys[:remainder_slots]:
        allocated[key] += 1

    if sum(allocated.values()) != total:
        raise RuntimeError("largest remainder allocation failed to preserve total.")

    return allocated
