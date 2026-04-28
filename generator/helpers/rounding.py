from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

USD_QUANTIZER = Decimal("0.01")


def to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, bool):
        raise TypeError("bool is not a valid numeric input for to_decimal().")
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, float):
        decimal_value = Decimal(str(value))
    elif isinstance(value, str):
        decimal_value = Decimal(value)
    else:
        raise TypeError(f"unsupported type for to_decimal(): {type(value)!r}")

    if not decimal_value.is_finite():
        raise ValueError("numeric inputs must be finite.")
    return decimal_value


def quantize_usd(
    value: Decimal | float | int | str,
    *,
    rounding: str = ROUND_HALF_UP,
) -> Decimal:
    return to_decimal(value).quantize(USD_QUANTIZER, rounding=rounding)


def intify_non_negative(
    value: Decimal | float | int | str,
) -> int:
    decimal_value = to_decimal(value)
    if decimal_value < 0:
        raise ValueError("intify_non_negative() requires a non-negative value.")
    return int(decimal_value.to_integral_value(rounding=ROUND_CEILING))


def finalize_spend_total(
    fixed_cost_usd: Decimal | float | int | str,
    variable_cost_usd: Decimal | float | int | str,
) -> Decimal:
    fixed_cost = quantize_usd(fixed_cost_usd)
    variable_cost = quantize_usd(variable_cost_usd)
    return quantize_usd(fixed_cost + variable_cost)
