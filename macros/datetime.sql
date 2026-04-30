{% macro utc_timestamp(expression) -%}
    {{ return(adapter.dispatch('utc_timestamp')(expression)) }}
{%- endmacro %}

{% macro default__utc_timestamp(expression) -%}
    timezone('UTC', {{ expression }})
{%- endmacro %}

{% macro bigquery__utc_timestamp(expression) -%}
    {{ expression }}
{%- endmacro %}

{% macro utc_date(expression) -%}
    {{ return(adapter.dispatch('utc_date')(expression)) }}
{%- endmacro %}

{% macro default__utc_date(expression) -%}
    cast({{ utc_timestamp(expression) }} as date)
{%- endmacro %}

{% macro bigquery__utc_date(expression) -%}
    date({{ expression }})
{%- endmacro %}

{% macro timestamp_diff_hours(end_expression, start_expression) -%}
    {{ return(adapter.dispatch('timestamp_diff_hours')(end_expression, start_expression)) }}
{%- endmacro %}

{% macro default__timestamp_diff_hours(end_expression, start_expression) -%}
    epoch({{ end_expression }} - {{ start_expression }}) / 3600.0
{%- endmacro %}

{% macro bigquery__timestamp_diff_hours(end_expression, start_expression) -%}
    timestamp_diff({{ end_expression }}, {{ start_expression }}, second) / 3600.0
{%- endmacro %}

{% macro month_start_date(expression) -%}
    {{ return(adapter.dispatch('month_start_date')(expression)) }}
{%- endmacro %}

{% macro default__month_start_date(expression) -%}
    cast(date_trunc('month', {{ expression }}) AS DATE)
{%- endmacro %}

{% macro bigquery__month_start_date(expression) -%}
    date_trunc({{ expression }}, month)
{%- endmacro %}

{% macro month_end_timestamp(expression) -%}
    {{ return(adapter.dispatch('month_end_timestamp')(expression)) }}
{%- endmacro %}

{% macro default__month_end_timestamp(expression) -%}
    cast(
      date_trunc('month', {{ expression }})
      + INTERVAL 1 MONTH
      - INTERVAL 1 SECOND
      AS TIMESTAMP
    )
{%- endmacro %}

{% macro bigquery__month_end_timestamp(expression) -%}
    timestamp_sub(
      timestamp(date_add(date_trunc({{ expression }}, month), interval 1 month)),
      interval 1 second
    )
{%- endmacro %}
