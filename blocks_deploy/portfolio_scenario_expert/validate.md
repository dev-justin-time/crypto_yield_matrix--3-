# Canonical CSV validation report

This repository uses one dataset file for every local and deployed agent: `yield_data.csv`.
The file intentionally retains all 118 supplied rows and its embedded `source_file`/`source_row` provenance columns. The provenance labels describe row origin; they are not additional files to load.

## Dataset contract

- Canonical file: `yield_data.csv`
- Data rows: **118**
- Columns: **61**
- SHA-256: `dd1152d0466a45f1c12d6fe497a2cc2b0c49b369c320deb79ea7bd3896a9df5d`
- Deployment copies checked: **11**
- Duplicate symbol count: **59** symbols; these are retained because the supplied canonical file contains all provenance rows.
- Generated asset catalog: **59** rows and **59** per-asset files.
- Asset snapshot coverage: **9** source-backed, **50** canonical-only.
- Normalized quote exports: **59** per-asset files; statuses: {'unavailable': 50, 'source_snapshot': 9}.
- Alternate dataset files checked: **0** (only embedded provenance labels remain in the canonical file).

## Embedded provenance labels

- Embedded provenance labels: **2** labels across 118 rows.

## Checks

- Canonical row and column shape: **PASS**
- Aggregate formula checks: **PASS**
- Deployment copies byte-identical to root: **PASS**
- Alternate dataset files absent: **PASS**
- Dictionary contains every canonical CSV field: **PASS**
- Generated asset catalog coverage: **PASS**
- Normalized quote exports: **PASS**
- Deployment quote mirrors: **PASS**

## Agent rule

All handlers accept only `source_file: "yield_data.csv"` (or omit it to use that default). The generated `asset_catalog.csv` and `csv/assets/*.csv` files are evidence-first enrichments: source-backed fields are labeled, unavailable fields remain blank, and they must not replace the canonical source or be treated as live data. Because the canonical file contains repeated symbols, model-training workflows must preserve the provenance fields and must not treat repeated provenance rows as independent time observations without a documented row-selection policy.

No validation issues found.
