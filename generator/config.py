from __future__ import annotations

from copy import deepcopy
from datetime import date
from types import MappingProxyType

from .types import RowCountRange, RuntimeConfig

SPEC_VERSION = "v0.1.0"

GENERATOR_SEED = 18790314

TIME_CONFIG = {
    "n_months": 12,
    "anchor_month": "2025-12-01",
}

RAW_TARGETS = {
    "raw_tool_catalog_rows": 5,
    "raw_user_directory_rows": 198,
    "raw_access_requests_rows": 553,
    "raw_usage_events_daily_rows": 30000,
    "raw_tool_spend_monthly_rows": 313,
}

RAW_TARGET_RANGES: dict[str, RowCountRange] = {
    "raw_access_requests_rows": (500, 600),
    "raw_usage_events_daily_rows": (27200, 32000),
    "raw_tool_spend_monthly_rows": (290, 350),
}

TOOL_CATEGORY_VALUES = (
    "chat_assistant",
    "coding_assistant",
    "search_assistant",
    "multimodal_assistant",
)

DEPLOYMENT_SCOPE_VALUES = (
    "enterprise",
    "team",
)

RISK_TIER_VALUES = (
    "low",
    "medium",
    "high",
)

JOB_LEVEL_VALUES = (
    "individual_contributor",
    "manager",
    "director",
)

EMPLOYMENT_STATUS_VALUES = (
    "active",
    "inactive",
)

REQUEST_PURPOSE_VALUES = (
    "analysis",
    "engineering",
    "research",
    "operations",
    "content",
)

DATA_CLASSIFICATION_VALUES = (
    "public",
    "internal",
    "confidential",
    "restricted",
)

REQUEST_STATUS_VALUES = (
    "pending",
    "approved",
    "rejected",
)

ALLOWED_VALUES = {
    "tool_category": TOOL_CATEGORY_VALUES,
    "deployment_scope": DEPLOYMENT_SCOPE_VALUES,
    "risk_tier": RISK_TIER_VALUES,
    "job_level": JOB_LEVEL_VALUES,
    "employment_status": EMPLOYMENT_STATUS_VALUES,
    "request_purpose": REQUEST_PURPOSE_VALUES,
    "data_classification": DATA_CLASSIFICATION_VALUES,
    "request_status": REQUEST_STATUS_VALUES,
}

GENERATOR_CONFIG_CORE = {
    "seed": GENERATOR_SEED,
    "time": dict(TIME_CONFIG),
    "targets": dict(RAW_TARGETS),
    "target_ranges": dict(RAW_TARGET_RANGES),
    "allowed_values": {key: tuple(values) for key, values in ALLOWED_VALUES.items()},
}

BASE_ENTITY_CONFIG = {
    "n_departments": 3,
    "n_teams": 6,
    "n_tools": 5,
    "n_users": 198,
    "n_months": 12,
}

ORG_CONFIG = {
    "departments": [
        "Data",
        "Engineering",
        "Operations",
    ],
    "teams": [
        {
            "team_name": "Data Platform",
            "department_name": "Data",
            "size": 33,
        },
        {
            "team_name": "Analytics",
            "department_name": "Data",
            "size": 33,
        },
        {
            "team_name": "Backend",
            "department_name": "Engineering",
            "size": 35,
        },
        {
            "team_name": "Product Engineering",
            "department_name": "Engineering",
            "size": 35,
        },
        {
            "team_name": "Security",
            "department_name": "Operations",
            "size": 31,
        },
        {
            "team_name": "Business Operations",
            "department_name": "Operations",
            "size": 31,
        },
    ],
}

TOOL_CONFIG = [
    {
        "tool_code": "chatgpt_enterprise",
        "tool_name": "ChatGPT Enterprise",
        "vendor_name": "OpenAI",
        "tool_category": "chat_assistant",
        "deployment_scope": "enterprise",
        "risk_tier": "medium",
        "is_active": True,
        "homepage_url": "https://openai.com/chatgpt/enterprise/",
    },
    {
        "tool_code": "claude_enterprise",
        "tool_name": "Claude Enterprise",
        "vendor_name": "Anthropic",
        "tool_category": "chat_assistant",
        "deployment_scope": "enterprise",
        "risk_tier": "medium",
        "is_active": True,
        "homepage_url": "https://www.anthropic.com/enterprise",
    },
    {
        "tool_code": "gemini_enterprise",
        "tool_name": "Gemini Enterprise",
        "vendor_name": "Google",
        "tool_category": "multimodal_assistant",
        "deployment_scope": "enterprise",
        "risk_tier": "medium",
        "is_active": True,
        "homepage_url": "https://cloud.google.com/gemini-enterprise",
    },
    {
        "tool_code": "github_copilot_enterprise",
        "tool_name": "GitHub Copilot Enterprise",
        "vendor_name": "GitHub",
        "tool_category": "coding_assistant",
        "deployment_scope": "enterprise",
        "risk_tier": "low",
        "is_active": True,
        "homepage_url": "https://github.com/features/copilot",
    },
    {
        "tool_code": "perplexity_enterprise",
        "tool_name": "Perplexity Enterprise",
        "vendor_name": "Perplexity",
        "tool_category": "search_assistant",
        "deployment_scope": "enterprise",
        "risk_tier": "high",
        "is_active": True,
        "homepage_url": "https://www.perplexity.ai/enterprise",
    },
]

USER_JOB_LEVEL_CONFIG = {
    "job_level_values": [
        "individual_contributor",
        "manager",
        "director",
    ],
    "job_level_counts_by_team": {
        "Data Platform": {
            "individual_contributor": 29,
            "manager": 3,
            "director": 1,
        },
        "Analytics": {
            "individual_contributor": 29,
            "manager": 3,
            "director": 1,
        },
        "Backend": {
            "individual_contributor": 31,
            "manager": 3,
            "director": 1,
        },
        "Product Engineering": {
            "individual_contributor": 31,
            "manager": 3,
            "director": 1,
        },
        "Security": {
            "individual_contributor": 26,
            "manager": 4,
            "director": 1,
        },
        "Business Operations": {
            "individual_contributor": 28,
            "manager": 2,
            "director": 1,
        },
    },
}

USER_EMPLOYMENT_STATUS_CONFIG = {
    "employment_status_values": [
        "active",
        "inactive",
    ],
    "employment_status_counts_by_team_and_job_level": {
        "Data Platform": {
            "individual_contributor": {
                "active": 27,
                "inactive": 2,
            },
            "manager": {
                "active": 3,
                "inactive": 0,
            },
            "director": {
                "active": 1,
                "inactive": 0,
            },
        },
        "Analytics": {
            "individual_contributor": {
                "active": 26,
                "inactive": 3,
            },
            "manager": {
                "active": 3,
                "inactive": 0,
            },
            "director": {
                "active": 1,
                "inactive": 0,
            },
        },
        "Backend": {
            "individual_contributor": {
                "active": 30,
                "inactive": 1,
            },
            "manager": {
                "active": 3,
                "inactive": 0,
            },
            "director": {
                "active": 1,
                "inactive": 0,
            },
        },
        "Product Engineering": {
            "individual_contributor": {
                "active": 29,
                "inactive": 2,
            },
            "manager": {
                "active": 3,
                "inactive": 0,
            },
            "director": {
                "active": 1,
                "inactive": 0,
            },
        },
        "Security": {
            "individual_contributor": {
                "active": 24,
                "inactive": 2,
            },
            "manager": {
                "active": 4,
                "inactive": 0,
            },
            "director": {
                "active": 1,
                "inactive": 0,
            },
        },
        "Business Operations": {
            "individual_contributor": {
                "active": 27,
                "inactive": 1,
            },
            "manager": {
                "active": 2,
                "inactive": 0,
            },
            "director": {
                "active": 1,
                "inactive": 0,
            },
        },
    },
}

USER_PROFILE_CONFIG = {
    "job_level": USER_JOB_LEVEL_CONFIG,
    "employment_status": USER_EMPLOYMENT_STATUS_CONFIG,
    "derived_totals": {
        "individual_contributor_total": 174,
        "manager_total": 18,
        "director_total": 6,
        "active_total": 187,
        "inactive_total": 11,
    },
    "behavior_rules": {
        "inactive_user_rules": {
            "employment_status_is_fixed_for_full_window": True,
            "eligible_for_reviewer_pool": False,
            "may_submit_requests": False,
            "may_have_usage_rows": False,
        },
        "active_user_rules": {
            "eligible_for_reviewer_pool": True,
        },
    },
}

USER_GIVEN_NAME_POOL = (
    "Alex",
    "Taylor",
    "Jordan",
    "Morgan",
    "Casey",
    "Riley",
    "Avery",
    "Cameron",
    "Quinn",
    "Hayden",
    "Parker",
    "Reese",
    "Logan",
    "Jamie",
    "Rowan",
    "Elliot",
    "Devon",
    "Skyler",
)

USER_FAMILY_NAME_POOL = (
    "Carter",
    "Bennett",
    "Foster",
    "Hayes",
    "Brooks",
    "Murphy",
    "Cooper",
    "Reed",
    "Bailey",
    "Griffin",
    "Lawson",
    "Turner",
    "Walker",
    "Collins",
    "Kelly",
    "Rivera",
    "Chen",
    "Patel",
)

USER_NAME_CONFIG = {
    "selection_method": "stable_seed_ordered_cartesian_pairs",
    "format": "given_name_space_family_name",
    "given_name_pool": USER_GIVEN_NAME_POOL,
    "family_name_pool": USER_FAMILY_NAME_POOL,
    "expected_unique_name_pairs": RAW_TARGETS["raw_user_directory_rows"],
}

USER_EMAIL_CONFIG = {
    "domain": "synthetic.example.com",
    "format": "lowercase_given.family.rank4",
}

REQUEST_TEAM_TARGETS_ANNUAL = {
    "Data Platform": 105,
    "Analytics": 115,
    "Backend": 101,
    "Product Engineering": 95,
    "Security": 66,
    "Business Operations": 71,
}

REQUEST_MONTH_SEASONALITY = (
    0.90,
    0.92,
    0.95,
    0.98,
    1.00,
    1.03,
    1.05,
    1.04,
    1.02,
    1.00,
    1.05,
    1.06,
)

REQUEST_TOOL_WEIGHTS = {
    "Data Platform": {
        "chatgpt_enterprise": 0.23,
        "claude_enterprise": 0.20,
        "gemini_enterprise": 0.18,
        "github_copilot_enterprise": 0.24,
        "perplexity_enterprise": 0.15,
    },
    "Analytics": {
        "chatgpt_enterprise": 0.28,
        "claude_enterprise": 0.14,
        "gemini_enterprise": 0.22,
        "github_copilot_enterprise": 0.06,
        "perplexity_enterprise": 0.30,
    },
    "Backend": {
        "chatgpt_enterprise": 0.20,
        "claude_enterprise": 0.20,
        "gemini_enterprise": 0.12,
        "github_copilot_enterprise": 0.38,
        "perplexity_enterprise": 0.10,
    },
    "Product Engineering": {
        "chatgpt_enterprise": 0.22,
        "claude_enterprise": 0.20,
        "gemini_enterprise": 0.10,
        "github_copilot_enterprise": 0.40,
        "perplexity_enterprise": 0.08,
    },
    "Security": {
        "chatgpt_enterprise": 0.28,
        "claude_enterprise": 0.24,
        "gemini_enterprise": 0.14,
        "github_copilot_enterprise": 0.20,
        "perplexity_enterprise": 0.14,
    },
    "Business Operations": {
        "chatgpt_enterprise": 0.32,
        "claude_enterprise": 0.10,
        "gemini_enterprise": 0.20,
        "github_copilot_enterprise": 0.03,
        "perplexity_enterprise": 0.35,
    },
}

REQUEST_VOLUME_CONFIG = {
    "annual_team_targets": REQUEST_TEAM_TARGETS_ANNUAL,
    "month_seasonality": REQUEST_MONTH_SEASONALITY,
    "team_tool_weights": REQUEST_TOOL_WEIGHTS,
    "request_id_prefix": "req_",
    "request_id_zero_pad": 6,
}

TEAM_PURPOSE_BASE_WEIGHTS = {
    "Data Platform": {
        "analysis": 0.20,
        "engineering": 0.40,
        "research": 0.08,
        "operations": 0.25,
        "content": 0.07,
    },
    "Analytics": {
        "analysis": 0.45,
        "engineering": 0.08,
        "research": 0.25,
        "operations": 0.12,
        "content": 0.10,
    },
    "Backend": {
        "analysis": 0.08,
        "engineering": 0.62,
        "research": 0.06,
        "operations": 0.18,
        "content": 0.06,
    },
    "Product Engineering": {
        "analysis": 0.12,
        "engineering": 0.56,
        "research": 0.10,
        "operations": 0.10,
        "content": 0.12,
    },
    "Security": {
        "analysis": 0.15,
        "engineering": 0.25,
        "research": 0.10,
        "operations": 0.42,
        "content": 0.08,
    },
    "Business Operations": {
        "analysis": 0.22,
        "engineering": 0.08,
        "research": 0.10,
        "operations": 0.36,
        "content": 0.24,
    },
}

TOOL_PURPOSE_MULTIPLIERS = {
    "chatgpt_enterprise": {
        "analysis": 1.10,
        "engineering": 1.00,
        "research": 1.05,
        "operations": 1.00,
        "content": 1.15,
    },
    "claude_enterprise": {
        "analysis": 1.00,
        "engineering": 0.95,
        "research": 1.20,
        "operations": 0.95,
        "content": 1.10,
    },
    "gemini_enterprise": {
        "analysis": 1.10,
        "engineering": 0.85,
        "research": 1.15,
        "operations": 1.10,
        "content": 1.20,
    },
    "github_copilot_enterprise": {
        "analysis": 0.55,
        "engineering": 2.20,
        "research": 0.55,
        "operations": 0.85,
        "content": 0.25,
    },
    "perplexity_enterprise": {
        "analysis": 1.35,
        "engineering": 0.45,
        "research": 1.55,
        "operations": 1.00,
        "content": 0.60,
    },
}

PURPOSE_CLASSIFICATION_BASE_WEIGHTS = {
    "analysis": {
        "public": 0.08,
        "internal": 0.38,
        "confidential": 0.38,
        "restricted": 0.16,
    },
    "engineering": {
        "public": 0.06,
        "internal": 0.50,
        "confidential": 0.34,
        "restricted": 0.10,
    },
    "research": {
        "public": 0.18,
        "internal": 0.44,
        "confidential": 0.28,
        "restricted": 0.10,
    },
    "operations": {
        "public": 0.04,
        "internal": 0.36,
        "confidential": 0.44,
        "restricted": 0.16,
    },
    "content": {
        "public": 0.20,
        "internal": 0.52,
        "confidential": 0.22,
        "restricted": 0.06,
    },
}

TEAM_CLASSIFICATION_MULTIPLIERS = {
    "Data Platform": {
        "public": 0.85,
        "internal": 1.05,
        "confidential": 1.15,
        "restricted": 1.10,
    },
    "Analytics": {
        "public": 1.10,
        "internal": 1.05,
        "confidential": 1.00,
        "restricted": 0.88,
    },
    "Backend": {
        "public": 0.80,
        "internal": 1.10,
        "confidential": 1.12,
        "restricted": 1.00,
    },
    "Product Engineering": {
        "public": 0.95,
        "internal": 1.10,
        "confidential": 1.00,
        "restricted": 0.88,
    },
    "Security": {
        "public": 0.60,
        "internal": 0.95,
        "confidential": 1.20,
        "restricted": 1.45,
    },
    "Business Operations": {
        "public": 1.18,
        "internal": 1.10,
        "confidential": 0.90,
        "restricted": 0.65,
    },
}

REQUESTER_ASSIGNMENT_CONFIG = {
    "eligibility_rules": {
        "selection_uses_current_state_user_directory": True,
        "employment_status_must_be": "active",
        "team_must_match_request_team": True,
        "cross_team_requesters_forbidden": True,
    },
    "job_level_multipliers": {
        "individual_contributor": 1.00,
        "manager": 0.94,
        "director": 0.82,
    },
    "monthly_request_load_multipliers": {
        "0": 1.00,
        "1": 0.92,
        "2": 0.84,
        "3": 0.76,
        "4": 0.68,
        "5_plus": 0.60,
    },
    "same_tool_repeat_multipliers": {
        "0": 1.00,
        "1": 0.82,
        "2": 0.68,
        "3_plus": 0.54,
    },
    "deterministic_jitter_range": (0.985, 1.015),
    "selection_method": "weighted_row_by_row_with_stable_hash_tie_break",
}

REQUESTED_AT_CONFIG = {
    "timestamp_timezone": "UTC",
    "must_fall_within_allocated_request_month": True,
    "selection_method": "deterministic_weighted_date_then_hour",
    "weekday_weights": {
        "monday": 1.08,
        "tuesday": 1.05,
        "wednesday": 1.03,
        "thursday": 1.00,
        "friday": 0.96,
        "saturday": 0.12,
        "sunday": 0.06,
    },
    "month_position_bucket_weights": {
        "days_01_07": 0.94,
        "days_08_14": 1.00,
        "days_15_21": 1.05,
        "days_22_to_month_end_minus_1": 1.00,
        "final_calendar_day": 0.72,
    },
    "request_hour_weights_utc": {
        8: 0.05,
        9: 0.09,
        10: 0.12,
        11: 0.13,
        12: 0.10,
        13: 0.11,
        14: 0.11,
        15: 0.10,
        16: 0.09,
        17: 0.06,
        18: 0.03,
        19: 0.01,
    },
    "minute_range": (0, 59),
    "second_range": (0, 59),
    "date_jitter_range": (0.985, 1.015),
    "hour_jitter_range": (0.985, 1.015),
    "allow_duplicate_requested_at": True,
}

BUSINESS_JUSTIFICATION_TEXT_CONFIG = {
    "language": "en",
    "join_with_space": True,
    "include_tool_name": True,
    "include_team_name": False,
    "selection_method": "deterministic_hash_per_clause",
    "purpose_clauses": {
        "analysis": [
            "I need this tool to support recurring analytical work and faster synthesis of source material.",
            "This access is needed for analysis tasks that require summarization, comparison, and pattern review.",
            "I need this tool to improve turnaround time for analytical work and structured interpretation of internal materials.",
        ],
        "engineering": [
            "I need this tool to improve engineering productivity for implementation, debugging, and technical review.",
            "This access is needed to support day-to-day engineering work, including drafting, code interpretation, and iteration.",
            "I need this tool to reduce implementation overhead and speed up technical problem solving.",
        ],
        "research": [
            "I need this tool to support research-oriented exploration, source synthesis, and structured note generation.",
            "This access is needed for research workflows that require rapid comparison of references and hypothesis development.",
            "I need this tool to improve the speed and consistency of research support tasks.",
        ],
        "operations": [
            "I need this tool to support operational workflows, documentation handling, and process coordination.",
            "This access is needed for operational tasks that involve summarization, standardization, and response drafting.",
            "I need this tool to improve consistency and cycle time in operations work.",
        ],
        "content": [
            "I need this tool to support content drafting, editing, and structured rewriting tasks.",
            "This access is needed for content work that requires summarization, refinement, and format adaptation.",
            "I need this tool to improve content production speed while maintaining reviewable outputs.",
        ],
    },
    "tool_fit_clauses": {
        "chat_assistant": [
            "{tool_name} is appropriate because the work requires iterative prompting, drafting, and summarization.",
            "{tool_name} is a good fit because the workflow benefits from conversational refinement and rapid synthesis.",
        ],
        "coding_assistant": [
            "{tool_name} is appropriate because the work requires code-oriented assistance, review, and technical drafting.",
            "{tool_name} is a good fit because the workflow benefits from implementation support and debugging assistance.",
        ],
        "search_assistant": [
            "{tool_name} is appropriate because the work requires fast source discovery and comparison across references.",
            "{tool_name} is a good fit because the workflow depends on search-heavy information gathering and synthesis.",
        ],
        "multimodal_assistant": [
            "{tool_name} is appropriate because the work benefits from multimodal interpretation and structured extraction.",
            "{tool_name} is a good fit because the workflow involves mixed-format inputs and summarized outputs.",
        ],
    },
    "data_clauses": {
        "public": [
            "The expected inputs are limited to public or share-safe materials.",
            "The planned use is limited to public information and non-sensitive working materials.",
        ],
        "internal": [
            "The expected inputs are primarily internal business materials and routine working documents.",
            "The planned use includes internal-only information but does not require highly restricted handling.",
        ],
        "confidential": [
            "The expected inputs may include confidential internal material and require elevated handling discipline.",
            "The planned use includes sensitive internal content, so controlled use is required.",
        ],
        "restricted": [
            "The expected inputs may include restricted material and require the strongest handling controls.",
            "The planned use may involve highly sensitive information, so strict scope control is required.",
        ],
    },
    "control_clauses": {
        "public": [
            "Output will be reviewed before downstream use.",
            "Generated output will be treated as draft material and reviewed before use.",
        ],
        "internal": [
            "Use will remain within approved internal workflows, and output will be reviewed before use.",
            "The tool will be used within normal internal controls, with human review before downstream use.",
        ],
        "confidential": [
            "Use will follow internal handling standards, with careful prompt scoping and human review of outputs.",
            "The workflow will limit unnecessary exposure and require review before any downstream use.",
        ],
        "restricted": [
            "Use will be tightly scoped, limited to approved handling patterns, and subject to explicit human review.",
            "The workflow will minimize sensitive exposure and keep outputs within approved review boundaries.",
        ],
    },
}

REQUEST_SUBMISSION_CONFIG = {
    "purpose_values": REQUEST_PURPOSE_VALUES,
    "team_purpose_base_weights": TEAM_PURPOSE_BASE_WEIGHTS,
    "tool_purpose_multipliers": TOOL_PURPOSE_MULTIPLIERS,
    "classification_values": DATA_CLASSIFICATION_VALUES,
    "purpose_classification_base_weights": PURPOSE_CLASSIFICATION_BASE_WEIGHTS,
    "team_classification_multipliers": TEAM_CLASSIFICATION_MULTIPLIERS,
    "business_justification_text": BUSINESS_JUSTIFICATION_TEXT_CONFIG,
    "requester_assignment": REQUESTER_ASSIGNMENT_CONFIG,
    "requested_at": REQUESTED_AT_CONFIG,
}

REQUEST_STATUS_TARGETS = {
    "approved": 403,
    "rejected": 120,
    "pending": 30,
}

APPROVAL_MODEL_CONFIG = {
    "approval_probability_is_conditional_on": "reviewed_requests_only",
    "purpose_base_approval_probability": {
        "analysis": 0.82,
        "engineering": 0.86,
        "research": 0.84,
        "operations": 0.73,
        "content": 0.80,
    },
    "classification_approval_multipliers": {
        "public": 1.04,
        "internal": 1.00,
        "confidential": 0.84,
        "restricted": 0.58,
    },
    "risk_tier_approval_multipliers": {
        "low": 1.05,
        "medium": 1.00,
        "high": 0.75,
    },
}

PENDING_BACKLOG_CONFIG = {
    "final_pending_exact_target": 30,
    "month_end_open_targets_oldest_to_anchor": [
        5,
        8,
        10,
        12,
        14,
        17,
        19,
        21,
        23,
        25,
        28,
        30,
    ],
}

PENDING_BACKLOG_PRIORITY_MULTIPLIERS = {
    "team": {
        "Data Platform": 1.00,
        "Analytics": 0.94,
        "Backend": 0.88,
        "Product Engineering": 0.92,
        "Security": 1.22,
        "Business Operations": 1.10,
    },
    "purpose": {
        "analysis": 1.02,
        "engineering": 0.86,
        "research": 1.08,
        "operations": 1.18,
        "content": 0.92,
    },
    "classification": {
        "public": 0.72,
        "internal": 1.00,
        "confidential": 1.24,
        "restricted": 1.58,
    },
    "risk_tier": {
        "low": 0.86,
        "medium": 1.00,
        "high": 1.32,
    },
    "age_decay_by_months_open": {
        0: 1.00,
        1: 0.96,
        2: 0.90,
        3: 0.82,
        4: 0.72,
        5: 0.60,
    },
    "deterministic_jitter_range": (0.985, 1.015),
}

PENDING_REALISM_GUARDRAILS = {
    "soft_max_pending_age_days": 120,
    "max_share_pending_older_than_90d": 0.18,
    "prefer_recent_requests_for_final_pending": True,
}

REVIEW_LAG_CONFIG = {
    "timestamp_timezone": "UTC",
    "null_reviewed_at_for_statuses": ["pending"],
    "non_null_reviewed_at_for_statuses": ["approved", "rejected"],
    "same_month": {
        "base_lag_hours_by_status": {
            "approved": 22,
            "rejected": 34,
        },
        "classification_hour_adjustment": {
            "public": -6,
            "internal": 0,
            "confidential": 10,
            "restricted": 24,
        },
        "risk_tier_hour_adjustment": {
            "low": -4,
            "medium": 0,
            "high": 12,
        },
        "jitter_hours_range": (-6, 6),
        "min_lag_hours_by_status": {
            "approved": 4,
            "rejected": 8,
        },
        "max_lag_hours_by_status": {
            "approved": 120,
            "rejected": 168,
        },
        "review_hour_weights_utc": {
            8: 0.04,
            9: 0.08,
            10: 0.12,
            11: 0.14,
            12: 0.10,
            13: 0.12,
            14: 0.12,
            15: 0.10,
            16: 0.08,
            17: 0.06,
            18: 0.04,
            19: 0.01,
        },
        "minute_range": (0, 59),
        "second_range": (0, 59),
    },
    "carryover": {
        "base_day_offset_by_status": {
            "approved": 4,
            "rejected": 8,
        },
        "classification_day_adjustment": {
            "public": -1,
            "internal": 0,
            "confidential": 1,
            "restricted": 3,
        },
        "risk_tier_day_adjustment": {
            "low": -1,
            "medium": 0,
            "high": 2,
        },
        "jitter_days_range": (-2, 2),
        "max_day_offset_in_review_month": 24,
        "review_hour_weights_utc": {
            8: 0.04,
            9: 0.08,
            10: 0.12,
            11: 0.14,
            12: 0.10,
            13: 0.12,
            14: 0.12,
            15: 0.10,
            16: 0.08,
            17: 0.06,
            18: 0.04,
            19: 0.01,
        },
        "minute_range": (0, 59),
        "second_range": (0, 59),
    },
}

REVIEW_LAG_QA_RULES = {
    "approved_or_rejected_must_have_reviewed_at": True,
    "pending_must_have_null_reviewed_at": True,
    "reviewed_at_must_be_after_requested_at": True,
    "reviewed_at_must_fall_inside_assigned_review_month": True,
    "approved_median_lag_hours_lt_rejected_median_lag_hours": True,
    "restricted_median_lag_hours_gt_internal_median_lag_hours": True,
    "high_risk_median_lag_hours_gt_medium_risk_median_lag_hours": True,
}

REVIEWER_POOL_CONFIG = {
    "reviewer_pool_by_team": {
        "Security": 3,
        "Data Platform": 3,
        "Backend": 3,
        "Analytics": 2,
        "Product Engineering": 3,
        "Business Operations": 2,
    },
    "total_reviewers": 16,
    "eligibility_rules": {
        "employment_status_must_be": "active",
        "exclude_requester_from_candidate_set": True,
        "selection_method": "deterministic_hash_rank_within_team",
    },
}

REVIEWER_TEAM_BASE_WEIGHTS = {
    "Security": 3.20,
    "Business Operations": 1.25,
    "Data Platform": 1.20,
    "Backend": 1.05,
    "Analytics": 1.00,
    "Product Engineering": 0.95,
}

REVIEWER_TOOL_CATEGORY_MULTIPLIERS = {
    "Security": {
        "chat_assistant": 1.00,
        "coding_assistant": 0.80,
        "search_assistant": 1.10,
        "multimodal_assistant": 0.95,
    },
    "Business Operations": {
        "chat_assistant": 1.10,
        "coding_assistant": 0.60,
        "search_assistant": 1.20,
        "multimodal_assistant": 0.90,
    },
    "Data Platform": {
        "chat_assistant": 0.95,
        "coding_assistant": 1.15,
        "search_assistant": 0.85,
        "multimodal_assistant": 1.05,
    },
    "Backend": {
        "chat_assistant": 0.85,
        "coding_assistant": 1.35,
        "search_assistant": 0.70,
        "multimodal_assistant": 0.95,
    },
    "Analytics": {
        "chat_assistant": 1.05,
        "coding_assistant": 0.65,
        "search_assistant": 1.30,
        "multimodal_assistant": 1.00,
    },
    "Product Engineering": {
        "chat_assistant": 0.95,
        "coding_assistant": 1.25,
        "search_assistant": 0.75,
        "multimodal_assistant": 0.95,
    },
}

REVIEWER_CLASSIFICATION_MULTIPLIERS = {
    "Security": {
        "public": 0.80,
        "internal": 0.95,
        "confidential": 1.35,
        "restricted": 1.75,
    },
    "Business Operations": {
        "public": 1.25,
        "internal": 1.10,
        "confidential": 0.85,
        "restricted": 0.55,
    },
    "Data Platform": {
        "public": 0.95,
        "internal": 1.10,
        "confidential": 1.05,
        "restricted": 0.90,
    },
    "Backend": {
        "public": 0.90,
        "internal": 1.05,
        "confidential": 1.05,
        "restricted": 0.90,
    },
    "Analytics": {
        "public": 1.10,
        "internal": 1.05,
        "confidential": 0.90,
        "restricted": 0.70,
    },
    "Product Engineering": {
        "public": 0.90,
        "internal": 1.00,
        "confidential": 0.95,
        "restricted": 0.80,
    },
}

REVIEWER_RISK_TIER_MULTIPLIERS = {
    "Security": {
        "low": 0.80,
        "medium": 1.00,
        "high": 1.55,
    },
    "Business Operations": {
        "low": 1.15,
        "medium": 1.00,
        "high": 0.70,
    },
    "Data Platform": {
        "low": 1.05,
        "medium": 1.05,
        "high": 0.95,
    },
    "Backend": {
        "low": 1.20,
        "medium": 1.00,
        "high": 0.75,
    },
    "Analytics": {
        "low": 1.10,
        "medium": 1.00,
        "high": 0.80,
    },
    "Product Engineering": {
        "low": 1.15,
        "medium": 0.95,
        "high": 0.70,
    },
}

REVIEWER_RELATIONSHIP_MULTIPLIERS = {
    "self": 0.00,
    "same_team": 0.72,
    "same_department": 0.92,
    "different_department": 1.00,
}

REVIEWER_LOAD_BALANCING_CONFIG = {
    "monthly_load_alpha": 0.22,
    "annual_load_beta": 0.04,
    "deterministic_jitter_range": (0.985, 1.015),
}

REVIEWER_ASSIGNMENT_QA_RULES = {
    "pending_must_have_null_reviewed_by_user_id": True,
    "approved_or_rejected_must_have_non_null_reviewed_by_user_id": True,
    "reviewed_by_user_id_must_exist_in_raw_user_directory": True,
    "self_review_forbidden": True,
    "max_single_reviewer_share_of_reviewed_requests": 0.22,
    "restricted_or_high_risk_share_reviewed_by_security_team_min": 0.45,
    "public_or_low_risk_share_reviewed_by_security_team_max": 0.40,
}

REVIEW_COMMENT_PRESENCE_CONFIG = {
    "pending_comment_rule": "always_null",
    "approved_comment_probability_is_lookup_table": True,
    "approved_comment_probability": {
        "public": {
            "low": 0.28,
            "medium": 0.34,
            "high": 0.44,
        },
        "internal": {
            "low": 0.36,
            "medium": 0.44,
            "high": 0.56,
        },
        "confidential": {
            "low": 0.52,
            "medium": 0.62,
            "high": 0.74,
        },
        "restricted": {
            "low": 0.70,
            "medium": 0.82,
            "high": 0.92,
        },
    },
    "rejected_comment_rule": "always_present",
}

APPROVED_REVIEW_COMMENT_CONFIG = {
    "language": "en",
    "selection_method": "deterministic_hash_per_family",
    "family_weights": {
        "public": {
            "low": {
                "standard_approval": 0.70,
                "scope_limited_approval": 0.20,
                "control_emphasis_approval": 0.10,
            },
            "medium": {
                "standard_approval": 0.60,
                "scope_limited_approval": 0.25,
                "control_emphasis_approval": 0.15,
            },
            "high": {
                "standard_approval": 0.45,
                "scope_limited_approval": 0.30,
                "control_emphasis_approval": 0.25,
            },
        },
        "internal": {
            "low": {
                "standard_approval": 0.58,
                "scope_limited_approval": 0.25,
                "control_emphasis_approval": 0.17,
            },
            "medium": {
                "standard_approval": 0.48,
                "scope_limited_approval": 0.30,
                "control_emphasis_approval": 0.22,
            },
            "high": {
                "standard_approval": 0.34,
                "scope_limited_approval": 0.33,
                "control_emphasis_approval": 0.33,
            },
        },
        "confidential": {
            "low": {
                "standard_approval": 0.36,
                "scope_limited_approval": 0.32,
                "control_emphasis_approval": 0.32,
            },
            "medium": {
                "standard_approval": 0.25,
                "scope_limited_approval": 0.35,
                "control_emphasis_approval": 0.40,
            },
            "high": {
                "standard_approval": 0.16,
                "scope_limited_approval": 0.34,
                "control_emphasis_approval": 0.50,
            },
        },
        "restricted": {
            "low": {
                "standard_approval": 0.18,
                "scope_limited_approval": 0.36,
                "control_emphasis_approval": 0.46,
            },
            "medium": {
                "standard_approval": 0.10,
                "scope_limited_approval": 0.34,
                "control_emphasis_approval": 0.56,
            },
            "high": {
                "standard_approval": 0.05,
                "scope_limited_approval": 0.25,
                "control_emphasis_approval": 0.70,
            },
        },
    },
    "templates": {
        "standard_approval": [
            "Approved for the stated business use.",
            "Approved based on the submitted business need.",
            "Approved for the requested workflow as described.",
        ],
        "scope_limited_approval": [
            "Approved for the stated use case within the submitted scope.",
            "Approved for the requested workflow with the stated scope limitations.",
            "Approved for the documented use case and current business need.",
        ],
        "control_emphasis_approval": [
            "Approved with the expectation that use remains within approved handling controls and reviewed workflows.",
            "Approved with controlled use, limited prompt scope, and human review of outputs.",
            "Approved for business use with strict adherence to internal handling controls.",
        ],
    },
}

REJECTED_REVIEW_COMMENT_CONFIG = {
    "language": "en",
    "selection_method": "deterministic_hash_per_family",
    "family_weights": {
        "public": {
            "low": {
                "insufficient_justification": 0.35,
                "sensitivity_too_high": 0.00,
                "approved_alternative_exists": 0.40,
                "scope_mismatch": 0.25,
            },
            "medium": {
                "insufficient_justification": 0.38,
                "sensitivity_too_high": 0.08,
                "approved_alternative_exists": 0.30,
                "scope_mismatch": 0.24,
            },
            "high": {
                "insufficient_justification": 0.30,
                "sensitivity_too_high": 0.24,
                "approved_alternative_exists": 0.20,
                "scope_mismatch": 0.26,
            },
        },
        "internal": {
            "low": {
                "insufficient_justification": 0.36,
                "sensitivity_too_high": 0.06,
                "approved_alternative_exists": 0.30,
                "scope_mismatch": 0.28,
            },
            "medium": {
                "insufficient_justification": 0.34,
                "sensitivity_too_high": 0.18,
                "approved_alternative_exists": 0.22,
                "scope_mismatch": 0.26,
            },
            "high": {
                "insufficient_justification": 0.28,
                "sensitivity_too_high": 0.32,
                "approved_alternative_exists": 0.14,
                "scope_mismatch": 0.26,
            },
        },
        "confidential": {
            "low": {
                "insufficient_justification": 0.28,
                "sensitivity_too_high": 0.34,
                "approved_alternative_exists": 0.14,
                "scope_mismatch": 0.24,
            },
            "medium": {
                "insufficient_justification": 0.22,
                "sensitivity_too_high": 0.46,
                "approved_alternative_exists": 0.10,
                "scope_mismatch": 0.22,
            },
            "high": {
                "insufficient_justification": 0.16,
                "sensitivity_too_high": 0.58,
                "approved_alternative_exists": 0.06,
                "scope_mismatch": 0.20,
            },
        },
        "restricted": {
            "low": {
                "insufficient_justification": 0.14,
                "sensitivity_too_high": 0.60,
                "approved_alternative_exists": 0.06,
                "scope_mismatch": 0.20,
            },
            "medium": {
                "insufficient_justification": 0.10,
                "sensitivity_too_high": 0.70,
                "approved_alternative_exists": 0.04,
                "scope_mismatch": 0.16,
            },
            "high": {
                "insufficient_justification": 0.06,
                "sensitivity_too_high": 0.80,
                "approved_alternative_exists": 0.02,
                "scope_mismatch": 0.12,
            },
        },
    },
    "templates": {
        "insufficient_justification": [
            "Rejected because the submitted business justification does not support the requested level of access.",
            "Rejected because the current justification is not sufficient for approval.",
            "Rejected because the business need is not documented strongly enough for this request.",
        ],
        "sensitivity_too_high": [
            "Rejected because the stated data sensitivity is not appropriate for the requested access under current controls.",
            "Rejected because the requested use involves data sensitivity that exceeds the approved handling pattern.",
            "Rejected because the proposed use case is too sensitive for approval within the current control model.",
        ],
        "approved_alternative_exists": [
            "Rejected because an existing approved tool or workflow should be used for this need.",
            "Rejected because the request overlaps with an already supported alternative.",
            "Rejected because the stated use case should be handled through an approved existing option.",
        ],
        "scope_mismatch": [
            "Rejected because the requested access is broader than the documented business need.",
            "Rejected because the stated scope does not align with the requested access level.",
            "Rejected because the current request scope is not sufficiently bounded for approval.",
        ],
    },
}

REQUEST_REVIEW_CONFIG = {
    "request_status_targets": REQUEST_STATUS_TARGETS,
    "approval_model": APPROVAL_MODEL_CONFIG,
    "pending_backlog": PENDING_BACKLOG_CONFIG,
    "pending_priority_multipliers": PENDING_BACKLOG_PRIORITY_MULTIPLIERS,
    "pending_realism_guardrails": PENDING_REALISM_GUARDRAILS,
    "review_lag": REVIEW_LAG_CONFIG,
    "review_lag_qa": REVIEW_LAG_QA_RULES,
    "reviewer_pool": REVIEWER_POOL_CONFIG,
    "reviewer_team_base_weights": REVIEWER_TEAM_BASE_WEIGHTS,
    "reviewer_tool_category_multipliers": REVIEWER_TOOL_CATEGORY_MULTIPLIERS,
    "reviewer_classification_multipliers": REVIEWER_CLASSIFICATION_MULTIPLIERS,
    "reviewer_risk_tier_multipliers": REVIEWER_RISK_TIER_MULTIPLIERS,
    "reviewer_relationship_multipliers": REVIEWER_RELATIONSHIP_MULTIPLIERS,
    "reviewer_load_balancing": REVIEWER_LOAD_BALANCING_CONFIG,
    "reviewer_assignment_qa": REVIEWER_ASSIGNMENT_QA_RULES,
    "review_comment_presence": REVIEW_COMMENT_PRESENCE_CONFIG,
    "approved_review_comment": APPROVED_REVIEW_COMMENT_CONFIG,
    "rejected_review_comment": REJECTED_REVIEW_COMMENT_CONFIG,
}

DUPLICATE_REQUEST_POLICY_CONFIG = {
    "duplicate_unit": ["requester_user_id", "tool_code"],
    "sequence_sort_keys": ["requested_at", "request_id"],
    "max_requests_per_user_tool_pair": 3,
    "same_calendar_month_duplicates_forbidden": True,
    "later_request_after_approved_forbidden": True,
    "later_request_after_pending_forbidden": True,
    "all_non_final_requests_in_multi_request_sequence_must_be_rejected": True,
    "max_pending_requests_per_user_tool_pair": 1,
    "enforcement_strategy": {
        "preventive_downweighting_in_requester_assignment": True,
        "final_reconciliation_after_status_realization": True,
        "reassign_violating_rows_to_alternate_requesters_if_possible": True,
        "fail_if_no_feasible_reassignment_exists": True,
    },
}

APPROVED_PAIR_RECENT_ACTIVITY_CONFIG = {
    "approved_active_pairs_current_is_derived": True,
    "approved_but_inactive_pairs_current_exact_target": 24,
    "purpose_base_weight": {
        "analysis": 0.90,
        "engineering": 0.95,
        "research": 0.88,
        "operations": 0.82,
        "content": 0.86,
    },
    "classification_multipliers": {
        "public": 1.05,
        "internal": 1.00,
        "confidential": 0.93,
        "restricted": 0.78,
    },
    "risk_tier_multipliers": {
        "low": 1.05,
        "medium": 1.00,
        "high": 0.88,
    },
    "tool_category_multipliers": {
        "chat_assistant": 1.00,
        "coding_assistant": 1.08,
        "search_assistant": 0.96,
        "multimodal_assistant": 1.00,
    },
    "approval_age_bucket_multipliers": {
        "0_1_months": 0.82,
        "2_4_months": 0.97,
        "5_plus_months": 1.05,
    },
    "deterministic_jitter_range": (0.985, 1.015),
    "selection_method": "weighted_partition_with_derived_active_target",
}

UNAPPROVED_PAIR_ANOMALY_USAGE_CONFIG = {
    "used_without_approval_exact_target": 8,
    "candidate_universe_priority": [
        "rejected_request_exists",
        "pending_request_exists",
        "no_request_history",
    ],
    "tool_category_base_weight": {
        "chat_assistant": 0.012,
        "coding_assistant": 0.004,
        "search_assistant": 0.015,
        "multimodal_assistant": 0.010,
    },
    "classification_multipliers": {
        "public": 1.40,
        "internal": 1.00,
        "confidential": 0.55,
        "restricted": 0.25,
    },
    "risk_tier_multipliers": {
        "low": 1.30,
        "medium": 1.00,
        "high": 0.45,
    },
    "request_history_state_multipliers": {
        "rejected_request_exists": 1.35,
        "pending_request_exists": 0.85,
        "no_request_history": 0.55,
    },
    "deterministic_jitter_range": (0.985, 1.015),
    "selection_method": "weighted_partition_with_derived_active_target",
}

APPROVED_MONTHLY_ACTIVITY_CONFIG = {
    "pre_approval_month_activity_weight": 0.0,
    "purpose_base_weight": {
        "analysis": 0.56,
        "engineering": 0.72,
        "research": 0.50,
        "operations": 0.46,
        "content": 0.48,
    },
    "classification_multipliers": {
        "public": 1.05,
        "internal": 1.00,
        "confidential": 0.92,
        "restricted": 0.80,
    },
    "risk_tier_multipliers": {
        "low": 1.06,
        "medium": 1.00,
        "high": 0.86,
    },
    "tool_category_multipliers": {
        "chat_assistant": 1.02,
        "coding_assistant": 1.18,
        "search_assistant": 0.94,
        "multimodal_assistant": 1.00,
    },
    "months_since_approval_bucket_multipliers": {
        "0": 0.78,
        "1_2": 1.05,
        "3_5": 1.10,
        "6_plus": 0.96,
    },
    "deterministic_jitter_range": (0.985, 1.015),
}

# exact snippet を回収できなかった部分は、STEP9の最小ローカル補完として定義
CURRENT_STATE_TARGETS = {
    "used_without_approval_pairs_current": 8,
    "approved_but_inactive_pairs_current": 24,
}

CURRENT_STATE_RANGES = {
    "used_without_approval_pairs_current": (5, 12),
    "approved_but_inactive_pairs_current": (18, 32),
}

USAGE_GENERATION_ASSUMPTIONS = {
    "recent_window_days": 30,
    "approved_access_persists_once_granted": True,
    "inactive_users_must_have_no_usage_rows": True,
    "raw_usage_rows_exist_only_for_active_days": True,
    "anomaly_pairs_are_lighter_than_approved_normal_pairs": True,
}

DAILY_ACTIVITY_INTENSITY_CONFIG = {
    "active_days_model": "scaled_weighted_count",
    "base_active_days_by_pair_type": {
        "approved_normal": 10.0,
        "unapproved_anomaly": 3.2,
    },
    "active_days_bounds": {
        "approved_normal": {
            "min": 1,
            "max": 22,
        },
        "unapproved_anomaly": {
            "min": 1,
            "max": 8,
        },
    },
    "pair_type_multipliers": {
        "approved_normal": 1.00,
        "unapproved_anomaly": 0.48,
    },
    "tool_category_multipliers": {
        "chat_assistant": 1.00,
        "coding_assistant": 1.12,
        "search_assistant": 0.92,
        "multimodal_assistant": 0.98,
    },
    "classification_multipliers": {
        "public": 1.04,
        "internal": 1.00,
        "confidential": 0.92,
        "restricted": 0.84,
    },
    "deterministic_jitter_range": (0.985, 1.015),
    "row_target": RAW_TARGETS["raw_usage_events_daily_rows"],
    "row_range": RAW_TARGET_RANGES["raw_usage_events_daily_rows"],
}

USAGE_DATE_CONFIG = {
    "selection_method": "deterministic_weighted_without_replacement",
    "weekday_weights": {
        "monday": 1.03,
        "tuesday": 1.02,
        "wednesday": 1.01,
        "thursday": 1.00,
        "friday": 0.99,
        "saturday": 0.05,
        "sunday": 0.03,
    },
    "month_position_bucket_weights": {
        "days_01_07": 0.98,
        "days_08_14": 1.00,
        "days_15_21": 1.01,
        "days_22_to_month_end_minus_1": 1.02,
        "final_calendar_day": 0.98,
    },
    "date_jitter_range": (0.94, 1.06),
    "approved_normal_must_not_precede_first_approved_date": True,
}

SESSION_PROMPT_INTENSITY_CONFIG = {
    "session_count_model": "clipped_shifted_poisson",
    "prompt_count_model": "clipped_shifted_poisson_conditional_on_sessions",
    "session_count_bounds": {
        "min": 1,
        "max": 6,
    },
    "prompt_count_bounds": {
        "min": 3,
        "max": 30,
    },
    "session_base_by_tool_category": {
        "chat_assistant": 1.7,
        "coding_assistant": 2.5,
        "search_assistant": 1.55,
        "multimodal_assistant": 2.1,
    },
    "session_pair_type_multipliers": {
        "approved_normal": 1.00,
        "unapproved_anomaly": 0.45,
    },
    "session_classification_multipliers": {
        "public": 1.12,
        "internal": 1.00,
        "confidential": 0.88,
        "restricted": 0.72,
    },
    "prompt_base_by_tool_category": {
        "chat_assistant": 6.2,
        "coding_assistant": 4.8,
        "search_assistant": 3.2,
        "multimodal_assistant": 5.2,
    },
    "prompt_pair_type_multipliers": {
        "approved_normal": 1.00,
        "unapproved_anomaly": 0.62,
    },
    "prompt_classification_multipliers": {
        "public": 1.10,
        "internal": 1.00,
        "confidential": 0.88,
        "restricted": 0.72,
    },
    "prompt_multiplier_by_session_count": {
        1: 0.90,
        2: 1.20,
        3: 1.65,
        4: 2.15,
        5: 2.70,
        6: 3.25,
    },
    "session_jitter_range": (0.90, 1.10),
    "prompt_jitter_range": (0.88, 1.12),
}

TOKEN_INTENSITY_CONFIG = {
    "input_tokens_model": "clipped_count_model_conditioned_on_prompt_count",
    "output_tokens_model": "clipped_count_model_conditioned_on_prompt_count",
    "input_tokens_bounds": {
        "min_per_row": "prompt_count",
        "max": 24000,
    },
    "output_tokens_bounds": {
        "min_per_row": "prompt_count",
        "max": 30000,
    },
    "input_tokens_per_prompt_base_by_tool_category": {
        "chat_assistant": 170,
        "coding_assistant": 320,
        "search_assistant": 95,
        "multimodal_assistant": 230,
    },
    "output_tokens_per_prompt_base_by_tool_category": {
        "chat_assistant": 310,
        "coding_assistant": 150,
        "search_assistant": 90,
        "multimodal_assistant": 210,
    },
    "input_pair_type_multipliers": {
        "approved_normal": 1.00,
        "unapproved_anomaly": 0.70,
    },
    "output_pair_type_multipliers": {
        "approved_normal": 1.00,
        "unapproved_anomaly": 0.66,
    },
    "input_classification_multipliers": {
        "public": 1.10,
        "internal": 1.00,
        "confidential": 0.86,
        "restricted": 0.72,
    },
    "output_classification_multipliers": {
        "public": 1.12,
        "internal": 1.00,
        "confidential": 0.84,
        "restricted": 0.68,
    },
    "input_session_multipliers": {
        1: 0.92,
        2: 1.00,
        3: 1.14,
        4: 1.30,
        5: 1.48,
        6: 1.68,
    },
    "output_session_multipliers": {
        1: 0.94,
        2: 1.00,
        3: 1.12,
        4: 1.26,
        5: 1.42,
        6: 1.60,
    },
    "input_jitter_range": (0.85, 1.15),
    "output_jitter_range": (0.84, 1.16),
}

USAGE_COMPOSITE_UNIQUENESS_CONFIG = {
    "unique_key": ["usage_date", "user_id", "tool_code"],
    "multiple_rows_per_pair_day_forbidden": True,
}

USAGE_GENERATION_QA_RULES = {
    "raw_usage_events_daily_rows_must_be_within_target_range": True,
    "used_without_approval_pairs_current_must_match_exact_target": True,
    "approved_but_inactive_pairs_current_must_match_exact_target": True,
    "inactive_users_must_not_have_usage_rows": True,
    "approved_normal_usage_must_not_precede_first_approved_date": True,
    "session_prompt_token_fields_must_be_positive_for_emitted_rows": True,
    "usage_composite_uniqueness_must_hold": True,
}

USAGE_GENERATION_CONFIG = {
    "approved_pair_recent_activity": APPROVED_PAIR_RECENT_ACTIVITY_CONFIG,
    "unapproved_pair_anomaly_usage": UNAPPROVED_PAIR_ANOMALY_USAGE_CONFIG,
    "approved_monthly_activity": APPROVED_MONTHLY_ACTIVITY_CONFIG,
    "daily_activity_intensity": DAILY_ACTIVITY_INTENSITY_CONFIG,
    "usage_generation_qa": USAGE_GENERATION_QA_RULES,
    "current_state_targets": CURRENT_STATE_TARGETS,
    "current_state_ranges": CURRENT_STATE_RANGES,
    "usage_assumptions": USAGE_GENERATION_ASSUMPTIONS,
    "usage_date": USAGE_DATE_CONFIG,
    "session_prompt_intensity": SESSION_PROMPT_INTENSITY_CONFIG,
    "token_intensity": TOKEN_INTENSITY_CONFIG,
    "usage_composite_uniqueness": USAGE_COMPOSITE_UNIQUENESS_CONFIG,
}

SPEND_CONTRACT_ACTIVATION_CONFIG = {
    "exact_billed_row_target": RAW_TARGETS["raw_tool_spend_monthly_rows"],
    "activation_thresholds_by_tool_category": {
        "chat_assistant": {
            "approved_users_total_min": 2,
            "active_users_total_min": 1,
        },
        "coding_assistant": {
            "approved_users_total_min": 2,
            "active_users_total_min": 1,
        },
        "search_assistant": {
            "approved_users_total_min": 1,
            "active_users_total_min": 1,
        },
        "multimodal_assistant": {
            "approved_users_total_min": 2,
            "active_users_total_min": 1,
        },
    },
    "procurement_lag_months_by_risk_tier": {
        "low": 0,
        "medium": 1,
        "high": 2,
    },
    "contract_persistence_rule": "once_billed_persist_to_anchor_month",
    "exact_row_target_correction": (
        "advance_or_delay_contract_starts_by_priority_with_stable_hash_tie_break"
    ),
}

LICENSED_SEATS_CONFIG = {
    "seat_multiplier_from_approved_users_by_tool_category": {
        "chat_assistant": 0.85,
        "coding_assistant": 0.90,
        "search_assistant": 0.70,
        "multimodal_assistant": 0.82,
    },
    "seat_multiplier_from_active_users_by_tool_category": {
        "chat_assistant": 1.05,
        "coding_assistant": 0.95,
        "search_assistant": 1.15,
        "multimodal_assistant": 1.00,
    },
    "seat_buffer_by_tool_category": {
        "chat_assistant": 1,
        "coding_assistant": 1,
        "search_assistant": 1,
        "multimodal_assistant": 1,
    },
    "min_licensed_seats_if_billed": 2,
    "max_licensed_seats_global": 20,
    "team_size_cap": True,
}

FIXED_LICENSE_PRICING_CONFIG = {
    "synthetic_monthly_seat_price_usd_by_tool_code": {
        "chatgpt_enterprise": 60.00,
        "claude_enterprise": 54.00,
        "gemini_enterprise": 48.00,
        "github_copilot_enterprise": 39.00,
        "perplexity_enterprise": 42.00,
    },
    "team_contract_discount_multipliers": {
        "Data Platform": 0.98,
        "Analytics": 1.00,
        "Backend": 0.97,
        "Product Engineering": 0.97,
        "Security": 1.03,
        "Business Operations": 1.00,
    },
}

VARIABLE_USAGE_PRICING_CONFIG = {
    "per_session_rate_usd_by_tool_code": {
        "chatgpt_enterprise": 0.18,
        "claude_enterprise": 0.17,
        "gemini_enterprise": 0.16,
        "github_copilot_enterprise": 0.06,
        "perplexity_enterprise": 0.20,
    },
    "per_prompt_rate_usd_by_tool_code": {
        "chatgpt_enterprise": 0.012,
        "claude_enterprise": 0.011,
        "gemini_enterprise": 0.010,
        "github_copilot_enterprise": 0.003,
        "perplexity_enterprise": 0.008,
    },
    "active_user_overage_rate_usd_by_tool_code": {
        "chatgpt_enterprise": 6.00,
        "claude_enterprise": 5.50,
        "gemini_enterprise": 5.00,
        "github_copilot_enterprise": 4.00,
        "perplexity_enterprise": 5.00,
    },
    "variable_cost_floor_if_zero_usage": 0.00,
}

SPEND_GENERATION_MODEL_CONFIG = {
    "contract_activation": SPEND_CONTRACT_ACTIVATION_CONFIG,
    "licensed_seats": LICENSED_SEATS_CONFIG,
    "fixed_pricing": FIXED_LICENSE_PRICING_CONFIG,
    "variable_pricing": VARIABLE_USAGE_PRICING_CONFIG,
    "final_spend_rule": "spend_usd = fixed_license_cost_usd + variable_usage_cost_usd",
}

SPEND_GENERATION_ASSUMPTIONS = {
    "emit_rows_only_for_billed_team_tool_month": True,
    "licensed_seats_min": 2,
    "licensed_seats_max": 20,
    "require_positive_spend_for_emitted_row": True,
    "allow_zero_variable_usage_cost": True,
}

SPEND_GENERATION_QA_RULES = {
    "raw_tool_spend_monthly_rows_exact_target": RAW_TARGETS[
        "raw_tool_spend_monthly_rows"
    ],
    "raw_tool_spend_monthly_rows_range": RAW_TARGET_RANGES[
        "raw_tool_spend_monthly_rows"
    ],
    "licensed_seats_min_if_billed": 2,
    "licensed_seats_max_global": 20,
    "licensed_seats_must_not_exceed_team_size": True,
    "fixed_license_cost_usd_must_be_positive_if_row_emitted": True,
    "variable_usage_cost_usd_must_be_non_negative": True,
    "spend_usd_must_equal_fixed_plus_variable": True,
    "zero_usage_rows_may_have_zero_variable_cost": True,
}

SPEND_COMPOSITE_UNIQUENESS_CONFIG = {
    "composite_key": [
        "billing_month",
        "team_name",
        "tool_code",
    ],
    "uniqueness_must_hold_at_raw_write_time": True,
    "one_billed_cell_emits_exactly_one_row": True,
    "non_billed_cells_emit_no_rows": True,
    "department_name_not_part_of_composite_key": True,
    "late_stage_drop_duplicates_forbidden": True,
    "collision_resolution_strategy": "treat_duplicate_billing_key_as_generation_error",
}

SPEND_ROUNDING_CONFIG = {
    "licensed_seats_integerization": "ceil_then_clip",
    "money_quantization": "0.01",
    "money_rounding_mode": "ROUND_HALF_UP",
    "spend_total_is_reassembled_from_quantized_components": True,
}

SPEND_GENERATION_CONFIG = {
    "contract_activation": SPEND_CONTRACT_ACTIVATION_CONFIG,
    "licensed_seats": LICENSED_SEATS_CONFIG,
    "fixed_license_pricing": FIXED_LICENSE_PRICING_CONFIG,
    "variable_usage_pricing": VARIABLE_USAGE_PRICING_CONFIG,
    "model": SPEND_GENERATION_MODEL_CONFIG,
    "assumptions": SPEND_GENERATION_ASSUMPTIONS,
    "qa_rules": SPEND_GENERATION_QA_RULES,
    "composite_uniqueness": SPEND_COMPOSITE_UNIQUENESS_CONFIG,
    "rounding": SPEND_ROUNDING_CONFIG,
}


def build_runtime_config() -> RuntimeConfig:
    anchor_month = date.fromisoformat(TIME_CONFIG["anchor_month"])
    if anchor_month.day != 1:
        raise ValueError(
            "TIME_CONFIG['anchor_month'] must be the first calendar day of a month."
        )

    n_months = int(TIME_CONFIG["n_months"])
    if n_months < 1:
        raise ValueError("TIME_CONFIG['n_months'] must be >= 1.")

    raw_targets = MappingProxyType(dict(RAW_TARGETS))
    raw_target_ranges = MappingProxyType(dict(RAW_TARGET_RANGES))
    allowed_values = MappingProxyType(
        {key: tuple(values) for key, values in ALLOWED_VALUES.items()}
    )
    base_entity_config = MappingProxyType(dict(BASE_ENTITY_CONFIG))
    org_config = MappingProxyType(
        {
            "departments": tuple(ORG_CONFIG["departments"]),
            "teams": tuple(team.copy() for team in ORG_CONFIG["teams"]),
        }
    )
    tool_config = tuple(tool.copy() for tool in TOOL_CONFIG)
    user_profile_config = MappingProxyType(deepcopy(USER_PROFILE_CONFIG))
    user_name_config = MappingProxyType(
        {
            "selection_method": USER_NAME_CONFIG["selection_method"],
            "format": USER_NAME_CONFIG["format"],
            "given_name_pool": tuple(USER_NAME_CONFIG["given_name_pool"]),
            "family_name_pool": tuple(USER_NAME_CONFIG["family_name_pool"]),
            "expected_unique_name_pairs": int(
                USER_NAME_CONFIG["expected_unique_name_pairs"]
            ),
        }
    )
    user_email_config = MappingProxyType(
        {
            "domain": USER_EMAIL_CONFIG["domain"],
            "format": USER_EMAIL_CONFIG["format"],
        }
    )
    request_volume_config = MappingProxyType(
        {
            "annual_team_targets": deepcopy(
                REQUEST_VOLUME_CONFIG["annual_team_targets"]
            ),
            "month_seasonality": tuple(
                float(value) for value in REQUEST_VOLUME_CONFIG["month_seasonality"]
            ),
            "team_tool_weights": deepcopy(REQUEST_VOLUME_CONFIG["team_tool_weights"]),
            "request_id_prefix": REQUEST_VOLUME_CONFIG["request_id_prefix"],
            "request_id_zero_pad": int(REQUEST_VOLUME_CONFIG["request_id_zero_pad"]),
        }
    )
    request_submission_config = MappingProxyType(
        {
            "purpose_values": tuple(REQUEST_SUBMISSION_CONFIG["purpose_values"]),
            "team_purpose_base_weights": deepcopy(
                REQUEST_SUBMISSION_CONFIG["team_purpose_base_weights"]
            ),
            "tool_purpose_multipliers": deepcopy(
                REQUEST_SUBMISSION_CONFIG["tool_purpose_multipliers"]
            ),
            "classification_values": tuple(
                REQUEST_SUBMISSION_CONFIG["classification_values"]
            ),
            "purpose_classification_base_weights": deepcopy(
                REQUEST_SUBMISSION_CONFIG["purpose_classification_base_weights"]
            ),
            "team_classification_multipliers": deepcopy(
                REQUEST_SUBMISSION_CONFIG["team_classification_multipliers"]
            ),
            "business_justification_text": deepcopy(
                REQUEST_SUBMISSION_CONFIG["business_justification_text"]
            ),
            "requester_assignment": deepcopy(
                REQUEST_SUBMISSION_CONFIG["requester_assignment"]
            ),
            "requested_at": deepcopy(REQUEST_SUBMISSION_CONFIG["requested_at"]),
        }
    )

    request_review_config = MappingProxyType(
        {
            "request_status_targets": deepcopy(
                REQUEST_REVIEW_CONFIG["request_status_targets"]
            ),
            "approval_model": deepcopy(REQUEST_REVIEW_CONFIG["approval_model"]),
            "pending_backlog": deepcopy(REQUEST_REVIEW_CONFIG["pending_backlog"]),
            "pending_priority_multipliers": deepcopy(
                REQUEST_REVIEW_CONFIG["pending_priority_multipliers"]
            ),
            "pending_realism_guardrails": deepcopy(
                REQUEST_REVIEW_CONFIG["pending_realism_guardrails"]
            ),
            "review_lag": deepcopy(REQUEST_REVIEW_CONFIG["review_lag"]),
            "review_lag_qa": deepcopy(REQUEST_REVIEW_CONFIG["review_lag_qa"]),
            "reviewer_pool": deepcopy(REQUEST_REVIEW_CONFIG["reviewer_pool"]),
            "reviewer_team_base_weights": deepcopy(
                REQUEST_REVIEW_CONFIG["reviewer_team_base_weights"]
            ),
            "reviewer_tool_category_multipliers": deepcopy(
                REQUEST_REVIEW_CONFIG["reviewer_tool_category_multipliers"]
            ),
            "reviewer_classification_multipliers": deepcopy(
                REQUEST_REVIEW_CONFIG["reviewer_classification_multipliers"]
            ),
            "reviewer_risk_tier_multipliers": deepcopy(
                REQUEST_REVIEW_CONFIG["reviewer_risk_tier_multipliers"]
            ),
            "reviewer_relationship_multipliers": deepcopy(
                REQUEST_REVIEW_CONFIG["reviewer_relationship_multipliers"]
            ),
            "reviewer_load_balancing": deepcopy(
                REQUEST_REVIEW_CONFIG["reviewer_load_balancing"]
            ),
            "reviewer_assignment_qa": deepcopy(
                REQUEST_REVIEW_CONFIG["reviewer_assignment_qa"]
            ),
            "review_comment_presence": deepcopy(
                REQUEST_REVIEW_CONFIG["review_comment_presence"]
            ),
            "approved_review_comment": deepcopy(
                REQUEST_REVIEW_CONFIG["approved_review_comment"]
            ),
            "rejected_review_comment": deepcopy(
                REQUEST_REVIEW_CONFIG["rejected_review_comment"]
            ),
        }
    )

    request_duplicate_policy_config = MappingProxyType(
        {
            "duplicate_unit": tuple(DUPLICATE_REQUEST_POLICY_CONFIG["duplicate_unit"]),
            "sequence_sort_keys": tuple(
                DUPLICATE_REQUEST_POLICY_CONFIG["sequence_sort_keys"]
            ),
            "max_requests_per_user_tool_pair": int(
                DUPLICATE_REQUEST_POLICY_CONFIG["max_requests_per_user_tool_pair"]
            ),
            "same_calendar_month_duplicates_forbidden": bool(
                DUPLICATE_REQUEST_POLICY_CONFIG[
                    "same_calendar_month_duplicates_forbidden"
                ]
            ),
            "later_request_after_approved_forbidden": bool(
                DUPLICATE_REQUEST_POLICY_CONFIG[
                    "later_request_after_approved_forbidden"
                ]
            ),
            "later_request_after_pending_forbidden": bool(
                DUPLICATE_REQUEST_POLICY_CONFIG["later_request_after_pending_forbidden"]
            ),
            "all_non_final_requests_in_multi_request_sequence_must_be_rejected": bool(
                DUPLICATE_REQUEST_POLICY_CONFIG[
                    "all_non_final_requests_in_multi_request_sequence_must_be_rejected"
                ]
            ),
            "max_pending_requests_per_user_tool_pair": int(
                DUPLICATE_REQUEST_POLICY_CONFIG[
                    "max_pending_requests_per_user_tool_pair"
                ]
            ),
            "enforcement_strategy": deepcopy(
                DUPLICATE_REQUEST_POLICY_CONFIG["enforcement_strategy"]
            ),
        }
    )

    usage_generation_config = MappingProxyType(
        {
            "approved_pair_recent_activity": deepcopy(
                USAGE_GENERATION_CONFIG["approved_pair_recent_activity"]
            ),
            "unapproved_pair_anomaly_usage": deepcopy(
                USAGE_GENERATION_CONFIG["unapproved_pair_anomaly_usage"]
            ),
            "approved_monthly_activity": deepcopy(
                USAGE_GENERATION_CONFIG["approved_monthly_activity"]
            ),
            "daily_activity_intensity": deepcopy(
                USAGE_GENERATION_CONFIG["daily_activity_intensity"]
            ),
            "usage_generation_qa": deepcopy(
                USAGE_GENERATION_CONFIG["usage_generation_qa"]
            ),
            "current_state_targets": deepcopy(
                USAGE_GENERATION_CONFIG["current_state_targets"]
            ),
            "current_state_ranges": deepcopy(
                USAGE_GENERATION_CONFIG["current_state_ranges"]
            ),
            "usage_assumptions": deepcopy(USAGE_GENERATION_CONFIG["usage_assumptions"]),
            "usage_date": deepcopy(USAGE_GENERATION_CONFIG["usage_date"]),
            "session_prompt_intensity": deepcopy(
                USAGE_GENERATION_CONFIG["session_prompt_intensity"]
            ),
            "token_intensity": deepcopy(USAGE_GENERATION_CONFIG["token_intensity"]),
            "usage_composite_uniqueness": deepcopy(
                USAGE_GENERATION_CONFIG["usage_composite_uniqueness"]
            ),
        }
    )

    spend_generation_config = MappingProxyType(
        {
            "contract_activation": deepcopy(
                SPEND_GENERATION_CONFIG["contract_activation"]
            ),
            "licensed_seats": deepcopy(SPEND_GENERATION_CONFIG["licensed_seats"]),
            "fixed_license_pricing": deepcopy(
                SPEND_GENERATION_CONFIG["fixed_license_pricing"]
            ),
            "variable_usage_pricing": deepcopy(
                SPEND_GENERATION_CONFIG["variable_usage_pricing"]
            ),
            "model": deepcopy(SPEND_GENERATION_CONFIG["model"]),
            "assumptions": deepcopy(SPEND_GENERATION_CONFIG["assumptions"]),
            "qa_rules": deepcopy(SPEND_GENERATION_CONFIG["qa_rules"]),
            "composite_uniqueness": deepcopy(
                SPEND_GENERATION_CONFIG["composite_uniqueness"]
            ),
            "rounding": deepcopy(SPEND_GENERATION_CONFIG["rounding"]),
        }
    )

    return RuntimeConfig(
        seed=GENERATOR_SEED,
        anchor_month=anchor_month,
        n_months=n_months,
        raw_targets=raw_targets,
        raw_target_ranges=raw_target_ranges,
        allowed_values=allowed_values,
        spec_version=SPEC_VERSION,
        base_entity_config=base_entity_config,
        org_config=org_config,
        tool_config=tool_config,
        user_profile_config=user_profile_config,
        user_name_config=user_name_config,
        user_email_config=user_email_config,
        request_volume_config=request_volume_config,
        request_submission_config=request_submission_config,
        request_review_config=request_review_config,
        request_duplicate_policy_config=request_duplicate_policy_config,
        usage_generation_config=usage_generation_config,
        spend_generation_config=spend_generation_config,
    )
