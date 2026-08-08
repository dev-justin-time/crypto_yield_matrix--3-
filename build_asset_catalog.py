"""Build evidence-first per-asset enrichment and quote exports.

The canonical yield_data.csv remains the only handler request source. This script
creates derived catalog outputs and normalized Yahoo-style quote exports; it
never invents market values for assets without a supplied snapshot.
"""

from __future__ import annotations

import csv
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / "yield_data.csv"
SOURCE_DIR = ROOT / "csv"
CATALOG = ROOT / "asset_catalog.csv"
ASSET_DIR = SOURCE_DIR / "assets"
QUOTE_DIR = SOURCE_DIR / "quotes"
DEPLOY_ROOT = ROOT / "blocks_deploy"

DERIVED_FIELDS = ("yield_momentum", "mcap_to_tvl", "risk_score", "yield_premium")
SNAPSHOT_FIELDS = (
    "snapshot_source_file", "snapshot_symbol", "snapshot_status",
    "snapshot_regular_market_time", "snapshot_market_cap_usd",
    "snapshot_price_usd", "snapshot_change_pct", "snapshot_volume_usd",
    "snapshot_average_volume_usd", "snapshot_52w_high_usd",
    "snapshot_52w_low_usd", "snapshot_circulating_supply",
    "snapshot_website", "snapshot_exchange",
)

# Stable export columns modeled on the supplied Yahoo/CoinMarketCap-style
# tables. Every generated quote file has this same header, even when values are
# unavailable. Empty values mean unavailable supplied evidence, never zero.
QUOTE_SOURCE_FIELDS = (
    "website", "twitter", "name", "description", "whitepaper", "maxAge",
    "priceHint", "previousClose", "open", "dayLow", "dayHigh",
    "regularMarketPreviousClose", "regularMarketOpen", "regularMarketDayLow",
    "regularMarketDayHigh", "volume", "regularMarketVolume", "averageVolume",
    "averageVolume10days", "averageDailyVolume10Day", "marketCap",
    "fiftyTwoWeekLow", "fiftyTwoWeekHigh", "allTimeHigh", "allTimeLow",
    "fiftyDayAverage", "twoHundredDayAverage", "currency", "fromCurrency",
    "toCurrency", "lastMarket", "coinMarketCapLink", "volume24Hr",
    "volumeAllCurrencies", "circulatingSupply", "maxSupply", "totalSupply",
    "tradeable", "fullyDilutedValue", "volume24HrMarketCapPercent", "quoteType",
    "symbol", "language", "region", "typeDisp", "quoteSourceName",
    "triggerable", "customPriceAlertConfidence", "regularMarketChangePercent",
    "regularMarketPrice", "exchange", "messageBoardId", "exchangeTimezoneName",
    "exchangeTimezoneShortName", "gmtOffSetMilliseconds", "market", "esgPopulated",
    "marketState", "corporateActions", "regularMarketTime", "shortName",
    "fiftyTwoWeekChangePercent", "fiftyDayAverageChange",
    "fiftyDayAverageChangePercent", "twoHundredDayAverageChange",
    "twoHundredDayAverageChangePercent", "sourceInterval", "exchangeDataDelayedBy",
    "longName", "cryptoTradeable", "hasPrePostMarketData",
    "firstTradeDateMilliseconds", "regularMarketChange", "regularMarketDayRange",
    "fullExchangeName", "averageDailyVolume3Month", "coinImageUrl", "logoUrl",
    "fiftyTwoWeekLowChange", "fiftyTwoWeekLowChangePercent", "fiftyTwoWeekRange",
    "fiftyTwoWeekHighChange", "fiftyTwoWeekHighChangePercent", "trailingPegRatio",
)
QUOTE_META_FIELDS = (
    "quote_status", "quote_source_file", "quote_symbol", "quote_as_of_epoch",
    "quote_as_of_iso", "quote_fields_present", "quote_completeness_pct",
    "yield_matrix_symbol", "yield_current_aggregate_pct", "yield_change_pp",
    "yield_category", "yield_source_file", "catalog_row_policy",
)
QUOTE_FIELDS = QUOTE_META_FIELDS + QUOTE_SOURCE_FIELDS


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


def source_quotes() -> dict[str, tuple[Path, dict[str, str]]]:
    quotes: dict[str, tuple[Path, dict[str, str]]] = {}
    for path in sorted(SOURCE_DIR.glob("table-*.csv")):
        rows = read_csv(path)
        if len(rows) != 1 or "symbol" not in rows[0]:
            continue
        raw = rows[0]
        raw_symbol = raw.get("symbol", "").strip()
        symbol = raw_symbol.removesuffix("-USD").upper()
        if symbol and symbol not in quotes:
            quotes[symbol] = (path, raw)
    return quotes


def quote_metadata(symbol: str, canonical: dict[str, str], source: tuple[Path, dict[str, str]] | None) -> dict[str, str]:
    if source is None:
        return {
            "quote_status": "unavailable",
            "quote_source_file": "",
            "quote_symbol": f"{symbol}-USD",
            "quote_as_of_epoch": "",
            "quote_as_of_iso": "",
            "quote_fields_present": "0",
            "quote_completeness_pct": "0",
        }
    path, raw = source
    epoch = raw.get("regularMarketTime", "")
    try:
        as_iso = datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError, OSError):
        as_iso = ""
    present = sum(bool(raw.get(field, "")) for field in QUOTE_SOURCE_FIELDS)
    return {
        "quote_status": "source_snapshot",
        "quote_source_file": path.relative_to(ROOT).as_posix(),
        "quote_symbol": raw.get("symbol") or f"{symbol}-USD",
        "quote_as_of_epoch": epoch,
        "quote_as_of_iso": as_iso,
        "quote_fields_present": str(present),
        "quote_completeness_pct": csv_value(round(present / len(QUOTE_SOURCE_FIELDS) * 100, 1)),
    }


def quote_row(symbol: str, canonical: dict[str, str], source: tuple[Path, dict[str, str]] | None) -> dict[str, str]:
    metadata = quote_metadata(symbol, canonical, source)
    raw = source[1] if source else {}
    row = {field: "" for field in QUOTE_FIELDS}
    row.update(metadata)
    row.update({field: raw.get(field, "") for field in QUOTE_SOURCE_FIELDS})
    # Keep the export usable in spreadsheet filters even for unavailable quotes.
    row["yield_matrix_symbol"] = symbol
    row["yield_current_aggregate_pct"] = canonical.get("agg_current", "")
    row["yield_change_pp"] = canonical.get("change_pp", "")
    row["yield_category"] = canonical.get("category", "")
    row["yield_source_file"] = canonical.get("source_file", "")
    row["catalog_row_policy"] = "quote export joined to first canonical row with source_file=yield_data.csv"
    return row


def build() -> tuple[list[dict[str, str]], list[Path]]:
    canonical_rows = read_csv(CANONICAL)
    selected: dict[str, dict[str, str]] = {}
    for row in canonical_rows:
        symbol = row.get("symbol", "").strip().upper()
        if symbol and row.get("source_file") == "yield_data.csv" and symbol not in selected:
            selected[symbol] = row
    if not selected:
        raise RuntimeError("canonical yield_data.csv has no current evidence rows")

    quotes = source_quotes()
    rows: list[dict[str, str]] = []
    quote_rows: dict[str, dict[str, str]] = {}
    for symbol in sorted(selected):
        canonical = selected[symbol]
        source = quotes.get(symbol)
        row = {key: canonical.get(key, "") for key in canonical}
        row.update(derived(canonical))
        row.update({field: "" for field in SNAPSHOT_FIELDS})
        quote_info = quote_metadata(symbol, canonical, source)
        if source:
            raw = source[1]
            row.update({
                "snapshot_source_file": quote_info["quote_source_file"],
                "snapshot_symbol": quote_info["quote_symbol"],
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
            })
        else:
            row["snapshot_status"] = "canonical_only"
        row.update(quote_info)
        row["quote_file"] = f"csv/quotes/{symbol}.csv"
        row["quote_join_policy"] = "raw supplied quote fields only; blank means unavailable"
        row["catalog_row_policy"] = "first canonical row with source_file=yield_data.csv"
        row["catalog_generated"] = "1"
        rows.append(row)
        quote_rows[symbol] = quote_row(symbol, canonical, source)

    headers = list(rows[0])
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    QUOTE_DIR.mkdir(parents=True, exist_ok=True)
    for old in ASSET_DIR.glob("*.csv"):
        old.unlink()
    for old in QUOTE_DIR.glob("*.csv"):
        old.unlink()
    with CATALOG.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    generated: list[Path] = [CATALOG]
    deployment_projects = [
        project for project in sorted(DEPLOY_ROOT.iterdir())
        if project.is_dir() and project.name != "crypto_yield_a2a_orchestrator"
    ]
    for project in deployment_projects:
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
        quote_path = QUOTE_DIR / f"{row['symbol']}.csv"
        with quote_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=QUOTE_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerow(quote_rows[row["symbol"]])
        generated.append(quote_path)

    # Quote exports are generated artifacts, not handler sources. Mirror them
    # into data-consuming native projects because catalog metadata links to the
    # per-asset export path for operator inspection and artifact downloads.
    for project in deployment_projects:
        deployment_quote_dir = project / "csv" / "quotes"
        deployment_quote_dir.mkdir(parents=True, exist_ok=True)
        for old in deployment_quote_dir.glob("*.csv"):
            old.unlink()
        for source_quote in sorted(QUOTE_DIR.glob("*.csv")):
            destination = deployment_quote_dir / source_quote.name
            shutil.copyfile(source_quote, destination)
            generated.append(destination)
    return rows, generated


if __name__ == "__main__":
    assets, files = build()
    source_count = sum(row["snapshot_status"] == "source_snapshot" for row in assets)
    print(f"generated assets: {len(assets)}")
    print(f"source-backed snapshots: {source_count}")
    print(f"canonical-only assets: {len(assets) - source_count}")
    print(f"generated quote exports: {len([p for p in files if p.parent == QUOTE_DIR])}")
    print(f"generated files: {len(files)}")
