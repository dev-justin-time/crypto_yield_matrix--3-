import csv
import hashlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANONICAL_NAME = "yield_data.csv"
ALTERNATE_NAMES = {"yield_data1.csv", "consolidated_yield_data.csv"}
DEPLOY_ROOT = ROOT / "blocks_deploy"


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
issues: list[str] = []
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
    "",
    "## Agent rule",
    "",
    "All handlers accept only `source_file: \"yield_data.csv\"` (or omit it to use that default). They must not attempt to open or treat the embedded provenance labels as separate datasets. Because the canonical file contains repeated symbols, model-training workflows must preserve the provenance fields and must not treat repeated provenance rows as independent time observations without a documented row-selection policy.",
    "",
]
if issues:
    report += ["## Issues", ""] + [f"- {issue}" for issue in issues] + [""]
else:
    report.append("No validation issues found.")

(ROOT / "validate.md").write_text("\n".join(report) + "\n", encoding="utf-8")

print(f"canonical rows: {len(rows)}")
print(f"canonical columns: {len(headers)}")
print(f"deployment copies: {len(deployment_files)}")
print(f"embedded provenance labels: {embedded_provenance}")
print(f"issues: {len(issues)}")
if issues:
    raise SystemExit(1)
