from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
CONTEXT_ALLOWLIST = {
    "validate.md",
    "DATA_DICTIONARY.md",
    "yield_data.csv",
    "index.html",
    "matrix.js",
    "styles.css",
}
YIELD_SOURCES = {"yield_data.csv"}


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
    return {"source_file": filename, "source_row": resolved_line, "symbol": row.get("symbol")}


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
        "provenance": {
            "mode": "repository_read_only",
            "sources": "Project context files only; no live network data was requested.",
            "source_file": source_file,
            "context_files": accessed,
        },
    }
    required = {"agent", "status", "summary", "findings", "assumptions", "limitations", "provenance"}
    if set(payload) != required:
        raise RuntimeError("common artifact envelope failed validation")
    return {"artifacts": [{"data": json.dumps(payload, indent=2), "mimeType": "application/json"}]}


def status(ctx: Any, message: str) -> None:
    callback = getattr(ctx, "report_status", None) or getattr(ctx, "reportStatus", None)
    if callback:
        callback(message)
