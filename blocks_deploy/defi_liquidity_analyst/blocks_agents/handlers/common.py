from __future__ import annotations

import csv
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
ASSET_CATALOG = ROOT / "asset_catalog.csv"
CONTEXT_ALLOWLIST = {
    "validate.md",
    "DATA_DICTIONARY.md",
    "yield_data.csv",
    "index.html",
    "matrix.js",
    "styles.css",
    "asset_catalog.csv",
}
YIELD_SOURCES = {"yield_data.csv"}

USER_VALUE_GUIDANCE: dict[str, dict[str, str]] = {
    "crypto_risk_analyst": {
        "decision_use": "Use yield together with drawdown, volatility, beta, and risk-adjusted measures to screen downside context.",
        "review_next": "Compare the result with liquidity and tokenomics evidence before making any allocation decision.",
        "do_not_infer": "A high yield or favorable risk metric is not a safety guarantee, expected return, or recommendation.",
    },
    "defi_liquidity_analyst": {
        "decision_use": "Use volume, TVL, activity, and trend fields to identify liquidity and exit-risk questions for follow-up.",
        "review_next": "Confirm live pool depth, slippage, venue concentration, and withdrawal constraints before acting.",
        "do_not_infer": "Snapshot volume or TVL is not a real-time liquidity guarantee and may include bots or routing activity.",
    },
    "tokenomics_sustainability_expert": {
        "decision_use": "Compare nominal yield with inflation, dilution, supply, and market-cap context to assess sustainability questions.",
        "review_next": "Check reward composition, unlock schedules, fees, lockups, and price exposure using current primary sources.",
        "do_not_infer": "Nominal-minus-inflation is a diagnostic proxy, not realized return or a complete real-yield calculation.",
    },
    "yield_methodology_expert": {
        "decision_use": "Use methodology notes and annualization flags to avoid treating unlike yield mechanisms as directly comparable.",
        "review_next": "Verify APR/APY conventions, compounding, lockups, fees, and reward assets with the provider.",
        "do_not_infer": "A displayed percentage is not necessarily an equivalent, guaranteed, or currently available return.",
    },
    "matrix_research_insights_agent": {
        "decision_use": "Use the matrix to prioritize assets and questions for deeper risk, liquidity, methodology, and provenance review.",
        "review_next": "Open the cited source rows and compare the supplied target labels with independently observed data before modeling.",
        "do_not_infer": "Dashboard target fields are not validated forecasts and should not be treated as predictions.",
    },
    "feature_engineering_expert": {
        "decision_use": "Use transparent derived features as reproducible research inputs and audit the formula inputs beside each result.",
        "review_next": "Check units, missing denominators, outliers, and chronological leakage before using a feature in a model.",
        "do_not_infer": "A derived score is not a validated signal, ranking, or investment recommendation.",
    },
    "portfolio_scenario_expert": {
        "decision_use": "Use the scenario fields to compare trade-offs under explicit constraints rather than request an automatic recommendation.",
        "review_next": "Add fees, taxes, lockups, covariance, position limits, and live execution assumptions to any real analysis.",
        "do_not_infer": "The scenario summary does not constitute portfolio advice, suitability assessment, or execution instruction.",
    },
}

DEFAULT_USER_VALUE = {
    "decision_use": "Use the findings as traceable research evidence to decide what requires deeper review.",
    "review_next": "Validate important claims against current primary sources and the cited provenance rows.",
    "do_not_infer": "This artifact is decision support, not financial advice, a guarantee, or a validated forecast.",
}


def task_payload(task: Any) -> dict[str, Any]:
    parts = getattr(task, "request_parts", None)
    if parts is None:
        parts = getattr(task, "requestParts", None)
    parts = parts or []
    first = parts[0] if parts else None
    raw = getattr(first, "text", None) if first is not None else None
    if raw is None and isinstance(first, dict):
        raw = first.get("text") or first.get("data")
    if isinstance(raw, dict):
        payload = raw
    elif isinstance(raw, str):
        try:
            value = json.loads(raw)
            payload = value if isinstance(value, dict) else {"question": raw}
        except json.JSONDecodeError:
            payload = {"question": raw}
    else:
        payload = {}
    validate_context_files(payload.get("files", []))
    return payload


def validate_context_files(filenames: Any) -> list[str]:
    if filenames is None or filenames == "":
        return []
    if isinstance(filenames, str) or not isinstance(filenames, (list, tuple)):
        raise ValueError("files must be an array of repository-relative context filenames")
    safe = []
    for filename in filenames:
        if not isinstance(filename, str) or not filename or filename.startswith(("/", "\\")):
            raise ValueError(f"unsafe context filename: {filename!r}")
        candidate = Path(filename)
        if candidate.is_absolute() or ".." in candidate.parts or filename not in CONTEXT_ALLOWLIST:
            raise ValueError(f"context filename is outside the declared read-only allowlist: {filename!r}")
        safe.append(filename)
    return safe


def read_context(filename: str) -> str:
    validate_context_files([filename])
    return (ROOT / filename).read_text(encoding="utf-8")


def load_csv(filename: str) -> list[dict[str, str]]:
    validate_context_files([filename])
    path = ROOT / filename
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_source(filename: str = "yield_data.csv") -> list[dict[str, str]]:
    if filename not in YIELD_SOURCES:
        raise ValueError(f"source_file must be one of {sorted(YIELD_SOURCES)}")
    return load_csv(filename)


@lru_cache(maxsize=1)
def load_asset_catalog() -> tuple[dict[str, str], ...]:
    """Load generated evidence-first asset enrichment without changing source policy."""
    if not ASSET_CATALOG.exists():
        return ()
    with ASSET_CATALOG.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def catalog_by_symbol() -> dict[str, dict[str, str]]:
    return {row.get("symbol", "").upper(): row for row in load_asset_catalog() if row.get("symbol")}


def asset_enrichment(symbol: str) -> dict[str, Any]:
    row = catalog_by_symbol().get(str(symbol).upper(), {})
    return {
        "coverage_status": row.get("snapshot_status", "unavailable"),
        "snapshot_source_file": row.get("snapshot_source_file") or None,
        "snapshot_price_usd": numeric_value(row, "snapshot_price_usd"),
        "snapshot_change_pct": numeric_value(row, "snapshot_change_pct"),
        "snapshot_market_cap_usd": numeric_value(row, "snapshot_market_cap_usd"),
        "snapshot_volume_usd": numeric_value(row, "snapshot_volume_usd"),
        "snapshot_52w_high_usd": numeric_value(row, "snapshot_52w_high_usd"),
        "snapshot_52w_low_usd": numeric_value(row, "snapshot_52w_low_usd"),
        "yield_momentum": numeric_value(row, "yield_momentum"),
        "mcap_to_tvl": numeric_value(row, "mcap_to_tvl"),
        "risk_score": numeric_value(row, "risk_score"),
        "yield_premium": numeric_value(row, "yield_premium"),
    }


def value(row: dict[str, str], field: str, default: float = 0.0) -> float:
    try:
        return float(row.get(field, default))
    except (TypeError, ValueError):
        return default


def select(rows: Iterable[dict[str, str]], payload: dict[str, Any]) -> list[dict[str, str]]:
    symbol = str(payload.get("symbol", "")).upper()
    category = str(payload.get("category", "")).lower()
    result = list(rows)
    if symbol:
        result = [row for row in result if row.get("symbol", "").upper() == symbol]
    if category:
        result = [row for row in result if row.get("category", "").lower() == category]
    return result


def numeric_value(row: dict[str, str], field: str) -> float | None:
    try:
        parsed = float(row.get(field, ""))
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def derived_features(row: dict[str, str]) -> dict[str, float | None]:
    trend = numeric_value(row, "yield_trend_slope")
    yield_volatility = numeric_value(row, "yield_volatility")
    market_cap = numeric_value(row, "mcap_end_current_usd")
    tvl = numeric_value(row, "tvl_usd")
    beta = numeric_value(row, "beta_vs_btc")
    price_volatility = numeric_value(row, "volatility_annualized_current")
    sharpe = numeric_value(row, "sharpe_ratio_current")
    aggregate = numeric_value(row, "agg_current")
    category_metric = numeric_value(row, "yield_vs_category_avg")
    return {
        "yield_momentum": trend * yield_volatility if trend is not None and yield_volatility is not None else None,
        "mcap_to_tvl": safe_divide(market_cap, tvl),
        "risk_score": safe_divide(beta * price_volatility if beta is not None and price_volatility is not None else None, sharpe),
        "yield_premium": aggregate - category_metric if aggregate is not None and category_metric is not None else None,
    }


def evidence(row: dict[str, str], filename: str, line: int | None = None) -> dict[str, Any]:
    resolved_line = line if line is not None else row.get("source_row")
    catalog = catalog_by_symbol().get(row.get("symbol", "").upper(), {})
    return {
        "source_file": filename,
        "source_row": resolved_line,
        "symbol": row.get("symbol"),
        "asset_catalog": {
            "status": catalog.get("snapshot_status", "unavailable"),
            "snapshot_source_file": catalog.get("snapshot_source_file") or None,
            "generated_fields": list(DERIVED_CATALOG_FIELDS),
        },
    }


DERIVED_CATALOG_FIELDS = ("yield_momentum", "mcap_to_tvl", "risk_score", "yield_premium")


def report(agent: str, status: str, summary: str, findings: list[dict[str, Any]],
           assumptions: list[str] | None = None, limitations: list[str] | None = None,
           source_file: str | None = None, context_files: list[str] | None = None) -> dict[str, Any]:
    if status not in {"PASS", "WARNING", "FAIL"}:
        raise ValueError("status must be PASS, WARNING, or FAIL")
    if not isinstance(findings, list):
        raise TypeError("findings must be a list")
    accessed = list(dict.fromkeys((context_files or []) + ([source_file] if source_file else [])))
    payload = {
        "agent": agent,
        "status": status,
        "summary": summary,
        "findings": findings,
        "assumptions": assumptions or [],
        "limitations": limitations or [],
        "user_value": USER_VALUE_GUIDANCE.get(agent, DEFAULT_USER_VALUE),
        "asset_catalog": {
            "available": bool(ASSET_CATALOG.exists()),
            "rows": len(load_asset_catalog()),
            "source_snapshot_rows": sum(row.get("snapshot_status") == "source_snapshot" for row in load_asset_catalog()),
            "canonical_only_rows": sum(row.get("snapshot_status") == "canonical_only" for row in load_asset_catalog()),
            "policy": "Generated enrichment only; canonical yield_data.csv remains the sole handler source.",
        },
        "provenance": {
            "mode": "repository_read_only",
            "sources": "Project context files only; no live network data was requested.",
            "source_file": source_file,
            "context_files": accessed,
        },
    }
    required = {"agent", "status", "summary", "findings", "assumptions", "limitations", "user_value", "asset_catalog", "provenance"}
    if set(payload) != required:
        raise RuntimeError("common artifact envelope failed validation")
    return {"artifacts": [{"data": json.dumps(payload, indent=2), "mimeType": "application/json"}]}


def status(ctx: Any, message: str) -> None:
    callback = getattr(ctx, "report_status", None) or getattr(ctx, "reportStatus", None)
    if callback:
        callback(message)
