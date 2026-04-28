from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from hashlib import blake2b
from typing import TypeVar

from generator.config import GENERATOR_SEED

_PERSONALIZATION = b"agw-v0_1_0"
_FIELD_SEPARATOR = "\x1f"

T = TypeVar("T")


def _stringify_part(part: object) -> str:
    if isinstance(part, datetime):
        return part.isoformat()
    if isinstance(part, date):
        return part.isoformat()
    if isinstance(part, Decimal):
        return format(part, "f")
    if part is None:
        return "<none>"
    return str(part)


def _serialize_parts(*parts: object) -> bytes:
    payload = _FIELD_SEPARATOR.join(_stringify_part(part) for part in parts)
    return payload.encode("utf-8")


def make_hash_bytes(
    *parts: object,
    seed: int = GENERATOR_SEED,
    namespace: str = "default",
    digest_size: int = 16,
) -> bytes:
    if not 1 <= digest_size <= 64:
        raise ValueError("digest_size must be in the inclusive range [1, 64].")

    payload = _serialize_parts(seed, namespace, *parts)
    return blake2b(
        payload,
        digest_size=digest_size,
        person=_PERSONALIZATION,
    ).digest()


def make_hash_int(
    *parts: object,
    seed: int = GENERATOR_SEED,
    namespace: str = "default",
    digest_size: int = 8,
) -> int:
    digest = make_hash_bytes(
        *parts,
        seed=seed,
        namespace=namespace,
        digest_size=digest_size,
    )
    return int.from_bytes(digest, byteorder="big", signed=False)


def make_deterministic_float(
    *parts: object,
    low: float,
    high: float,
    seed: int = GENERATOR_SEED,
    namespace: str = "float",
) -> float:
    if low > high:
        raise ValueError("low must be <= high.")

    if low == high:
        return float(low)

    raw = make_hash_int(
        *parts,
        seed=seed,
        namespace=namespace,
        digest_size=8,
    )
    unit = raw / ((1 << 64) - 1)
    return low + (high - low) * unit


def make_deterministic_jitter(
    *parts: object,
    low: float = 0.985,
    high: float = 1.015,
    seed: int = GENERATOR_SEED,
    namespace: str = "jitter",
) -> float:
    return make_deterministic_float(
        *parts,
        low=low,
        high=high,
        seed=seed,
        namespace=namespace,
    )


def make_deterministic_int(
    *parts: object,
    low: int,
    high: int,
    seed: int = GENERATOR_SEED,
    namespace: str = "int",
) -> int:
    if low > high:
        raise ValueError("low must be <= high.")

    if low == high:
        return int(low)

    span = high - low + 1
    raw = make_hash_int(
        *parts,
        seed=seed,
        namespace=namespace,
        digest_size=8,
    )
    return low + (raw % span)


def deterministic_weighted_choice(
    options: Sequence[T],
    weights: Sequence[float],
    *parts: object,
    seed: int = GENERATOR_SEED,
    namespace: str = "weighted_choice",
) -> T:
    if not options:
        raise ValueError("options must not be empty.")

    if len(options) != len(weights):
        raise ValueError("options and weights must have the same length.")

    validated_weights: list[float] = []
    for weight in weights:
        value = float(weight)
        if value < 0:
            raise ValueError("weights must be non-negative.")
        validated_weights.append(value)

    total_weight = sum(validated_weights)
    if total_weight <= 0:
        raise ValueError("sum(weights) must be > 0.")

    threshold = make_deterministic_float(
        *parts,
        low=0.0,
        high=total_weight,
        seed=seed,
        namespace=namespace,
    )

    cumulative = 0.0
    for option, weight in zip(options, validated_weights, strict=True):
        cumulative += weight
        if threshold <= cumulative:
            return option

    return options[-1]
