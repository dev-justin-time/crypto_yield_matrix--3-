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
- Removed dataset names: `yield_data1.csv`, `consolidated_yield_data.csv`.

## Embedded provenance labels

- `yield_data.csv`: 59 rows
- `yield_data1.csv`: 59 rows

## Checks

- Canonical row and column shape: **PASS**
- Aggregate formula checks: **PASS**
- Deployment copies byte-identical to root: **PASS**
- Alternate dataset files absent: **PASS**

## Agent rule

All handlers accept only `source_file: "yield_data.csv"` (or omit it to use that default). They must not attempt to open or treat the embedded provenance labels as separate datasets. Because the canonical file contains repeated symbols, model-training workflows must preserve the provenance fields and must not treat repeated provenance rows as independent time observations without a documented row-selection policy.

No validation issues found.
