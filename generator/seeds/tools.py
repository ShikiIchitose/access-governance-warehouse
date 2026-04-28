from __future__ import annotations

from typing import Any, Mapping

from generator.helpers.validation import ValidationError
from generator.types import RuntimeConfig, ToolRecord, ToolSeed

_REQUIRED_TOOL_KEYS = (
    "tool_code",
    "tool_name",
    "vendor_name",
    "tool_category",
    "deployment_scope",
    "risk_tier",
    "is_active",
    "homepage_url",
)


def _require_non_empty_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return normalized


def _require_optional_string(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_non_empty_string(value, field_name=field_name)


def _require_bool(value: Any, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a boolean.")
    return value


def _require_allowed_value(
    value: str,
    *,
    field_name: str,
    allowed_values: tuple[str, ...],
) -> str:
    if value not in allowed_values:
        raise ValidationError(
            f"{field_name} must be one of {allowed_values}, got {value!r}."
        )
    return value


def build_tool_order_lookup(tool_seed: ToolSeed) -> dict[str, int]:
    return {tool.tool_code: tool.tool_order for tool in tool_seed.tools}


def build_tool_seed(config: RuntimeConfig) -> ToolSeed:
    tool_config = config.tool_config
    if not tool_config:
        raise ValidationError("TOOL_CONFIG must not be empty.")

    allowed_values = config.allowed_values
    try:
        allowed_tool_categories = allowed_values["tool_category"]
        allowed_deployment_scopes = allowed_values["deployment_scope"]
        allowed_risk_tiers = allowed_values["risk_tier"]
    except KeyError as exc:
        raise ValidationError(
            f"Missing required allowed-values entry for tool seed validation: {exc}"
        ) from exc

    tools: list[ToolRecord] = []
    seen_tool_codes: set[str] = set()

    for tool_order, raw_tool in enumerate(tool_config):
        if not isinstance(raw_tool, Mapping):
            raise ValidationError("Every TOOL_CONFIG entry must be a mapping.")

        missing_keys = [key for key in _REQUIRED_TOOL_KEYS if key not in raw_tool]
        if missing_keys:
            raise ValidationError(
                f"TOOL_CONFIG entry is missing required keys: {missing_keys}"
            )

        tool_code = _require_non_empty_string(
            raw_tool["tool_code"],
            field_name="TOOL_CONFIG[].tool_code",
        )
        if tool_code in seen_tool_codes:
            raise ValidationError(f"Duplicate tool_code detected: {tool_code}")
        seen_tool_codes.add(tool_code)

        tool_name = _require_non_empty_string(
            raw_tool["tool_name"],
            field_name="TOOL_CONFIG[].tool_name",
        )
        vendor_name = _require_non_empty_string(
            raw_tool["vendor_name"],
            field_name="TOOL_CONFIG[].vendor_name",
        )
        tool_category = _require_allowed_value(
            _require_non_empty_string(
                raw_tool["tool_category"],
                field_name="TOOL_CONFIG[].tool_category",
            ),
            field_name="TOOL_CONFIG[].tool_category",
            allowed_values=allowed_tool_categories,
        )
        deployment_scope = _require_allowed_value(
            _require_non_empty_string(
                raw_tool["deployment_scope"],
                field_name="TOOL_CONFIG[].deployment_scope",
            ),
            field_name="TOOL_CONFIG[].deployment_scope",
            allowed_values=allowed_deployment_scopes,
        )
        risk_tier = _require_allowed_value(
            _require_non_empty_string(
                raw_tool["risk_tier"],
                field_name="TOOL_CONFIG[].risk_tier",
            ),
            field_name="TOOL_CONFIG[].risk_tier",
            allowed_values=allowed_risk_tiers,
        )
        is_active = _require_bool(
            raw_tool["is_active"],
            field_name="TOOL_CONFIG[].is_active",
        )
        homepage_url = _require_optional_string(
            raw_tool["homepage_url"],
            field_name="TOOL_CONFIG[].homepage_url",
        )

        tools.append(
            ToolRecord(
                tool_code=tool_code,
                tool_name=tool_name,
                vendor_name=vendor_name,
                tool_category=tool_category,
                deployment_scope=deployment_scope,
                risk_tier=risk_tier,
                is_active=is_active,
                homepage_url=homepage_url,
                tool_order=tool_order,
            )
        )

    expected_tools = config.raw_targets.get("raw_tool_catalog_rows")
    if expected_tools is None:
        raise ValidationError("Missing raw_tool_catalog_rows in raw_targets.")
    if len(tools) != expected_tools:
        raise ValidationError(
            "TOOL_CONFIG length does not match raw_tool_catalog_rows: "
            f"{len(tools)} != {expected_tools}"
        )

    tool_seed = ToolSeed(
        tools=tuple(tools),
        tool_order_lookup={tool.tool_code: tool.tool_order for tool in tools},
        active_tool_codes=tuple(tool.tool_code for tool in tools if tool.is_active),
    )
    return tool_seed
