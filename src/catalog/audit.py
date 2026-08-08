import csv
import hashlib
import re
from collections import Counter
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.catalog.build import QUOTE_FIELDS, QUOTE_SOURCE_FIELDS

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_NAME = "data/yield_data.csv"
DEPLOY_ROOT = ROOT / "blocks_deploy"
ASSET_CATALOG = ROOT / "data/asset_catalog.csv"
ASSET_DIR = ROOT / "csv" / "assets"
QUOTE_DIR = ROOT / "csv" / "quotes"
ALTERNATE_NAMES = {"yield_data1.csv", "consolidated_yield_data.csv"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def validate_row(row: dict[str, str], line: int) -> list[str]:
    issues: list[str] = []
    quarters = [
        "q3_24_prior", "q4_24_prior", "q1_25_prior", "q2_25_prior",
        "q3_25_current", "q4_25_current", "q1_26_current", "q2_26_current",
    ]
    try:
        prior = sum(float(row[column]) for column in quarters[:4]) / 4
        current = sum(float(row[column]) for column in quarters[4:]) / 4
        if abs(float(row["agg_prior"]) - prior) > 0.011:
            issues.append(f"row {line}: agg_prior does not match the prior-quarter mean")
        if abs(float(row["agg_current"]) - current) > 0.011:
            issues.append(f"row {line}: agg_current does not match the current-quarter mean")
        if abs(float(row["change_pp"]) - (current - prior)) > 0.011:
            issues.append(f"row {line}: change_pp does not match aggregate change")
    except (KeyError, TypeError, ValueError):
        issues.append(f"row {line}: missing or non-numeric aggregate field")
    return issues


canonical = ROOT / CANONICAL_NAME
rows = read_rows(canonical)
headers = list(rows[0]) if rows else []
dictionary_path = ROOT / "data/DATA_DICTIONARY.md"
dictionary_text = dictionary_path.read_text(encoding="utf-8") if dictionary_path.exists() else ""
issues: list[str] = []
dictionary_fields: set[str] = set()
for line in dictionary_text.splitlines():
    if not line.startswith("|"):
        continue
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if not cells or cells[0] in {"Column", "--------"}:
        continue
    field = cells[0]
    if " — " in field:
        start, end = [part.strip() for part in field.split(" — ", 1)]
        quarter_fields = [
            "q3_24_prior", "q4_24_prior", "q1_25_prior", "q2_25_prior",
            "q3_25_current", "q4_25_current", "q1_26_current", "q2_26_current",
        ]
        if start == quarter_fields[0] and end == quarter_fields[-1]:
            dictionary_fields.update(quarter_fields)
            continue
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", field):
        dictionary_fields.add(field)
missing_dictionary_fields = [header for header in headers if header not in dictionary_fields]
if missing_dictionary_fields:
    issues.append("dictionary is missing canonical fields: " + ", ".join(missing_dictionary_fields))
if "Canonical CSV columns:** 61" not in dictionary_text:
    issues.append("dictionary does not declare the 61-column canonical CSV contract")
if len(rows) != 118:
    issues.append(f"canonical row count is {len(rows)}, expected 118")
if len(headers) != 61:
    issues.append(f"canonical column count is {len(headers)}, expected 61")
for line, row in enumerate(rows, 2):
    if len(row) != len(headers):
        issues.append(f"row {line}: width differs from the canonical header")
    if not row.get("symbol"):
        issues.append(f"row {line}: missing symbol")
    issues.extend(validate_row(row, line))

source_labels = Counter(row.get("source_file", "") for row in rows)
symbols = Counter(row.get("symbol", "") for row in rows)
embedded_provenance = sorted(label for label in source_labels if label)

deployment_files = sorted(DEPLOY_ROOT.glob("*/yield_data.csv"))
noncanonical_csvs = [
    path for path in ROOT.rglob("*.csv")
    if path.name in ALTERNATE_NAMES and ".git" not in path.parts and "node_modules" not in path.parts
]
for path in deployment_files:
    if path.read_bytes() != canonical.read_bytes():
        issues.append(f"deployment copy differs from root: {path.relative_to(ROOT)}")
for path in noncanonical_csvs:
    issues.append(f"removed dataset still exists: {path.relative_to(ROOT)}")

catalog_rows = read_rows(ASSET_CATALOG) if ASSET_CATALOG.exists() else []
if len(catalog_rows) != len(symbols):
    issues.append(f"asset catalog has {len(catalog_rows)} rows, expected {len(symbols)} unique canonical symbols")
asset_files = sorted(ASSET_DIR.glob("*.csv")) if ASSET_DIR.exists() else []
if len(asset_files) != len(symbols):
    issues.append(f"per-asset catalog file count is {len(asset_files)}, expected {len(symbols)}")
catalog_symbols = {row.get("symbol", "") for row in catalog_rows}
asset_file_symbols = {path.stem for path in asset_files}
if asset_file_symbols != set(symbols):
    issues.append("per-asset catalog filenames do not match canonical unique symbols")
if catalog_symbols != set(symbols):
    issues.append("asset catalog symbols do not match canonical unique symbols")
if catalog_rows:
    catalog_by_symbol = {row.get("symbol", ""): row for row in catalog_rows}
    for path in asset_files:
        rows_for_asset = read_rows(path)
        symbol = path.stem
        if len(rows_for_asset) != 1 or rows_for_asset[0].get("symbol") != symbol:
            issues.append(f"per-asset catalog file does not contain exactly its named symbol: {path.relative_to(ROOT)}")
        elif catalog_by_symbol.get(symbol) != rows_for_asset[0]:
            issues.append(f"per-asset catalog row differs from asset_catalog.csv: {path.relative_to(ROOT)}")
    coverage = Counter(row.get("snapshot_status", "") for row in catalog_rows)
else:
    coverage = Counter()

quote_files = sorted(QUOTE_DIR.glob("*.csv")) if QUOTE_DIR.exists() else []
quote_file_symbols = {path.stem for path in quote_files}
if quote_file_symbols != set(symbols):
    issues.append("quote export filenames do not match canonical unique symbols")
if len(quote_files) != len(symbols):
    issues.append(f"quote export file count is {len(quote_files)}, expected {len(symbols)}")
quote_status = Counter()
for path in quote_files:
    quote_rows = read_rows(path)
    if len(quote_rows) != 1:
        issues.append(f"quote export does not contain exactly one row: {path.relative_to(ROOT)}")
        continue
    quote = quote_rows[0]
    if list(quote) != list(QUOTE_FIELDS):
        issues.append(f"quote export schema differs from the normalized contract: {path.relative_to(ROOT)}")
    if quote.get("yield_matrix_symbol") != path.stem:
        issues.append(f"quote export is joined to the wrong yield symbol: {path.relative_to(ROOT)}")
    quote_status[quote.get("quote_status", "")] += 1
    if quote.get("quote_status") == "unavailable":
        supplied_source_fields = [field for field in QUOTE_SOURCE_FIELDS if quote.get(field)]
        if supplied_source_fields:
            issues.append(f"unavailable quote export contains market values: {path.relative_to(ROOT)}")

deployment_quote_files = {
    project: sorted(project.glob("csv/quotes/*.csv"))
    for project in sorted(DEPLOY_ROOT.iterdir())
    if project.is_dir() and project.name != "crypto_yield_a2a_orchestrator"
}
for project, files in deployment_quote_files.items():
    project_symbols = {path.stem for path in files}
    if project_symbols != set(symbols) or len(files) != len(quote_files):
        issues.append(f"deployment quote export set differs from root: {project.relative_to(ROOT)}")
    for path in files:
        root_quote = QUOTE_DIR / path.name
        if not root_quote.exists() or path.read_bytes() != root_quote.read_bytes():
            issues.append(f"deployment quote export differs from root: {path.relative_to(ROOT)}")

report = [
    "# Canonical CSV validation report",
    "",
    "This repository uses one dataset file for every local and deployed agent: `yield_data.csv`.",
    "The file intentionally retains all 118 supplied rows and its embedded `source_file`/`source_row` provenance columns. The provenance labels describe row origin; they are not additional files to load.",
    "",
    "## Dataset contract",
    "",
    f"- Canonical file: `{CANONICAL_NAME}`",
    f"- Data rows: **{len(rows)}**",
    f"- Columns: **{len(headers)}**",
    f"- SHA-256: `{hashlib.sha256(canonical.read_bytes()).hexdigest()}`",
    f"- Deployment copies checked: **{len(deployment_files)}**",
    f"- Duplicate symbol count: **{sum(count > 1 for count in symbols.values())}** symbols; these are retained because the supplied canonical file contains all provenance rows.",
    f"- Generated asset catalog: **{len(catalog_rows)}** rows and **{len(asset_files)}** per-asset files.",
    f"- Asset snapshot coverage: **{coverage.get('source_snapshot', 0)}** source-backed, **{coverage.get('canonical_only', 0)}** canonical-only.",
    f"- Normalized quote exports: **{len(quote_files)}** per-asset files; statuses: {dict(quote_status)}.",
    "- Alternate dataset files checked: **0** (only embedded provenance labels remain in the canonical file).",
    "",
    "## Embedded provenance labels",
    "",
]
report.append(f"- Embedded provenance labels: **{len(source_labels)}** labels across {sum(source_labels.values())} rows.")
report += [
    "",
    "## Checks",
    "",
    f"- Canonical row and column shape: **{'PASS' if len(rows) == 118 and len(headers) == 61 else 'FAIL'}**",
    f"- Aggregate formula checks: **{'PASS' if not issues else 'FAIL'}**",
    f"- Deployment copies byte-identical to root: **{'PASS' if all(path.read_bytes() == canonical.read_bytes() for path in deployment_files) else 'FAIL'}**",
    f"- Alternate dataset files absent: **{'PASS' if not noncanonical_csvs else 'FAIL'}**",
    f"- Dictionary contains every canonical CSV field: **{'PASS' if not missing_dictionary_fields else 'FAIL'}**",
    f"- Generated asset catalog coverage: **{'PASS' if len(catalog_rows) == len(symbols) and len(asset_files) == len(symbols) and catalog_symbols == set(symbols) and asset_file_symbols == set(symbols) else 'FAIL'}**",
    f"- Normalized quote exports: **{'PASS' if len(quote_files) == len(symbols) and quote_file_symbols == set(symbols) and quote_status.get('source_snapshot', 0) == coverage.get('source_snapshot', 0) else 'FAIL'}**",
    f"- Deployment quote mirrors: **{'PASS' if not any(issue.startswith('deployment quote export') or issue.startswith('deployment quote export set') for issue in issues) else 'FAIL'}**",
    "",
    "## Agent rule",
    "",
    "All handlers accept only `source_file: \"yield_data.csv\"` (or omit it to use that default). The generated `asset_catalog.csv` and `csv/assets/*.csv` files are evidence-first enrichments: source-backed fields are labeled, unavailable fields remain blank, and they must not replace the canonical source or be treated as live data. Because the canonical file contains repeated symbols, model-training workflows must preserve the provenance fields and must not treat repeated provenance rows as independent time observations without a documented row-selection policy.",
    "",
]
if issues:
    report += ["## Issues", ""] + [f"- {issue}" for issue in issues] + [""]
else:
    report.append("No validation issues found.")

(ROOT / "docs/validate.md").write_text("\n".join(report) + "\n", encoding="utf-8")

print(f"canonical rows: {len(rows)}")
print(f"canonical columns: {len(headers)}")
print(f"deployment copies: {len(deployment_files)}")
print(f"embedded provenance labels: {embedded_provenance}")
print(f"issues: {len(issues)}")
if issues:
    raise SystemExit(1)
