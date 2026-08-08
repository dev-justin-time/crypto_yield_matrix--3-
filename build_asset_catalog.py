"""Build evidence-first per-asset CSVs from canonical and supplied source tables.

The canonical yield_data.csv remains the only handler request source. This script
creates derived catalog outputs; it never invents values for missing snapshots.
"""

from __future__ import annotations

import csv
import math
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / "yield_data.csv"
SOURCE_DIR = ROOT / "csv"
CATALOG = ROOT / "asset_catalog.csv"
ASSET_DIR = SOURCE_DIR / "assets"
DEPLOY_ROOT = ROOT / "blocks_deploy"

QUARTERS = (
    "q3_24_prior", "q4_24_prior", "q1_25_prior", "q2_25_prior",
    "q3_25_current", "q4_25_current", "q1_26_current", "q2_26_current",
)
DERIVED_FIELDS = ("yield_momentum", "mcap_to_tvl", "risk_score", "yield_premium")
SNAPSHOT_FIELDS = (
    "snapshot_source_file",
    "snapshot_symbol",
    "snapshot_status",
    "snapshot_regular_market_time",
    "snapshot_market_cap_usd",
    "snapshot_price_usd",
    "snapshot_change_pct",
    "snapshot_volume_usd",
    "snapshot_average_volume_usd",
    "snapshot_52w_high_usd",
    "snapshot_52w_low_usd",
    "snapshot_circulating_supply",
    "snapshot_website",
    "snapshot_exchange",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, str], field: str) -> float | None:
    try:
        value = float(row.get(field, ""))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.10g}"
    return str(value)


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def derived(row: dict[str, str]) -> dict[str, str]:
    trend = as_float(row, "yield_trend_slope")
    volatility = as_float(row, "yield_volatility")
    market_cap = as_float(row, "mcap_end_current_usd")
    tvl = as_float(row, "tvl_usd")
    beta = as_float(row, "beta_vs_btc")
    price_volatility = as_float(row, "volatility_annualized_current")
    sharpe = as_float(row, "sharpe_ratio_current")
    aggregate = as_float(row, "agg_current")
    category_gap = as_float(row, "yield_vs_category_avg")
    return {
        "yield_momentum": csv_value(trend * volatility if trend is not None and volatility is not None else None),
        "mcap_to_tvl": csv_value(safe_divide(market_cap, tvl)),
        "risk_score": csv_value(safe_divide(beta * price_volatility if beta is not None and price_volatility is not None else None, sharpe)),
        "yield_premium": csv_value(aggregate - category_gap if aggregate is not None and category_gap is not None else None),
    }


def source_snapshots() -> dict[str, dict[str, str]]:
    snapshots: dict[str, dict[str, str]] = {}
    for path in sorted(SOURCE_DIR.glob("table-*.csv")):
        rows = read_csv(path)
        if len(rows) != 1 or "symbol" not in rows[0]:
            continue
        raw = rows[0]
        raw_symbol = raw.get("symbol", "")
        symbol = raw_symbol.removesuffix("-USD")
        if not symbol or symbol in snapshots:
            continue
        snapshots[symbol] = {
            "snapshot_source_file": path.relative_to(ROOT).as_posix(),
            "snapshot_symbol": raw_symbol,
            "snapshot_status": "source_snapshot",
            "snapshot_regular_market_time": raw.get("regularMarketTime", ""),
            "snapshot_market_cap_usd": raw.get("marketCap", ""),
            "snapshot_price_usd": raw.get("regularMarketPrice", ""),
            "snapshot_change_pct": raw.get("regularMarketChangePercent", ""),
            "snapshot_volume_usd": raw.get("regularMarketVolume", ""),
            "snapshot_average_volume_usd": raw.get("averageVolume", ""),
            "snapshot_52w_high_usd": raw.get("fiftyTwoWeekHigh", ""),
            "snapshot_52w_low_usd": raw.get("fiftyTwoWeekLow", ""),
            "snapshot_circulating_supply": raw.get("circulatingSupply", ""),
            "snapshot_website": raw.get("website", ""),
            "snapshot_exchange": raw.get("exchange", ""),
        }
    return snapshots


def build() -> tuple[list[dict[str, str]], list[Path]]:
    canonical_rows = read_csv(CANONICAL)
    selected: dict[str, dict[str, str]] = {}
    for row in canonical_rows:
        symbol = row.get("symbol", "").strip().upper()
        # The first canonical row is the current evidence row selected by the
        # existing source-row policy; repeated rows remain in yield_data.csv.
        if symbol and row.get("source_file") == "yield_data.csv" and symbol not in selected:
            selected[symbol] = row
    if not selected:
        raise RuntimeError("canonical yield_data.csv has no current evidence rows")

    snapshots = source_snapshots()
    rows: list[dict[str, str]] = []
    for symbol in sorted(selected):
        canonical = selected[symbol]
        row = {key: canonical.get(key, "") for key in canonical}
        row.update(derived(canonical))
        row.update({field: "" for field in SNAPSHOT_FIELDS})
        snapshot = snapshots.get(symbol)
        if snapshot:
            row.update(snapshot)
        else:
            row["snapshot_status"] = "canonical_only"
        row["catalog_row_policy"] = "first canonical row with source_file=yield_data.csv"
        row["catalog_generated"] = "1"
        rows.append(row)

    headers = list(rows[0])
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for old in ASSET_DIR.glob("*.csv"):
        old.unlink()
    with CATALOG.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    generated: list[Path] = [CATALOG]
    for project in sorted(DEPLOY_ROOT.iterdir()):
        if project.is_dir() and project.name != "crypto_yield_a2a_orchestrator":
            destination = project / CATALOG.name
            shutil.copyfile(CATALOG, destination)
            generated.append(destination)
    for row in rows:
        path = ASSET_DIR / f"{row['symbol']}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
            writer.writeheader()
            writer.writerow(row)
        generated.append(path)
    return rows, generated


if __name__ == "__main__":
    assets, files = build()
    source_count = sum(row["snapshot_status"] == "source_snapshot" for row in assets)
    print(f"generated assets: {len(assets)}")
    print(f"source-backed snapshots: {source_count}")
    print(f"canonical-only assets: {len(assets) - source_count}")
    print(f"generated files: {len(files)}")
