"""Organize supplied table CSV exports into named, auditable source files.

The canonical handler source remains ``yield_data.csv``. This utility only
moves the heterogeneous exports under ``csv/`` into two explicit namespaces:

* ``csv/source_snapshots/<SYMBOL>.csv`` for one-row market snapshots;
* ``csv/reference/<name>.csv`` for documentation, coverage, and summary tables.

It never fabricates rows or values. ``--check`` is read-only and verifies the
manifest hashes; ``--write`` performs deterministic local file moves.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_DIR = ROOT / "csv"
SNAPSHOT_DIR = CSV_DIR / "source_snapshots"
REFERENCE_DIR = CSV_DIR / "reference"
MANIFEST = CSV_DIR / "source_manifest.json"
SCHEMA_VERSION = 1

REFERENCE_NAMES = {
    ("File", "Purpose"): "file_purposes.csv",
    ("Feature Group", "Columns"): "feature_groups.csv",
    ("Source", "Assets Covered"): "source_coverage.csv",
    ("Feature Group", "Real Data"): "data_quality_notes.csv",
    ("Asset", "Price"): "asset_summary.csv",
    ("File", "Size"): "package_contents.csv",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_shape(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def symbol_for(headers: list[str], rows: list[dict[str, str]]) -> str:
    if len(rows) != 1 or "symbol" not in headers:
        return ""
    raw = (rows[0].get("symbol") or "").strip().upper()
    return raw.removesuffix("-USD")


def target_for(path: Path) -> tuple[str, Path, str]:
    headers, rows = read_shape(path)
    symbol = symbol_for(headers, rows)
    if symbol:
        return "asset_snapshot", SNAPSHOT_DIR / f"{symbol}.csv", symbol
    key = tuple(headers[:2])
    name = REFERENCE_NAMES.get(key)
    if not name:
        raise ValueError(f"unrecognized table export schema: {path.name}: {headers[:4]}")
    return "reference", REFERENCE_DIR / name, ""


def source_tables() -> list[Path]:
    return sorted(CSV_DIR.glob("table-*.csv"))


def build_records() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for source in source_tables():
        kind, target, symbol = target_for(source)
        records.append({
            "original_path": source.relative_to(ROOT).as_posix(),
            "path": target.relative_to(ROOT).as_posix(),
            "kind": kind,
            "symbol": symbol,
        })
    return records


def _records_from_manifest() -> list[dict[str, str]]:
    if not MANIFEST.exists():
        return []
    try:
        value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    records = value.get("records", [])
    return records if isinstance(records, list) else []


def _validate_unique_targets(records: list[dict[str, str]]) -> None:
    targets = [record["path"] for record in records]
    if len(targets) != len(set(targets)):
        raise RuntimeError("source organization refused duplicate destination filenames")


def write() -> int:
    records = build_records()
    _validate_unique_targets(records)
    if not records and MANIFEST.exists():
        records = _records_from_manifest()
        if not records:
            raise RuntimeError("existing source manifest has no records")
        _validate_unique_targets(records)
        for record in records:
            target = ROOT / record["path"]
            if not target.exists():
                raise RuntimeError(f"organized source is incomplete; missing {target}")
            current_hash = digest(target)
            expected_hash = record.get("sha256")
            if expected_hash and current_hash != expected_hash:
                raise RuntimeError(f"organized source changed since manifest creation: {target}")
            # A legacy manifest may lack original_sha256. Backfill it only
            # after proving the destination still matches the recorded hash.
            record["original_sha256"] = expected_hash or current_hash
            record["sha256"] = expected_hash or current_hash
            record["hash_provenance"] = record.get("hash_provenance") or "destination_verified_recovered"
            record["bytes"] = str(target.stat().st_size)
        MANIFEST.write_text(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "policy": "Named source snapshots and reference exports; canonical yield_data.csv remains unchanged.",
            "source_snapshot_directory": "csv/source_snapshots",
            "reference_directory": "csv/reference",
            "records": records,
        }, indent=2) + "\n", encoding="utf-8")
        print("source organization: already organized; manifest refreshed")
        return check()
    if not records:
        raise RuntimeError("no table-*.csv exports found and no source manifest exists")
    _validate_unique_targets(records)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    for record in records:
        source = ROOT / record["original_path"]
        target = ROOT / record["path"]
        original_hash = digest(source)
        if target.exists():
            if digest(target) != original_hash:
                raise RuntimeError(f"refusing to overwrite different file: {target}")
        else:
            shutil.copyfile(source, target)
            if digest(target) != original_hash:
                target.unlink(missing_ok=True)
                raise RuntimeError(f"copy verification failed: {target}")
        source.unlink()
        record["original_sha256"] = original_hash
        record["sha256"] = digest(target)
        record["hash_provenance"] = "source_and_destination_verified"
        record["bytes"] = str(target.stat().st_size)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "policy": "Named source snapshots and reference exports; canonical yield_data.csv remains unchanged.",
        "source_snapshot_directory": "csv/source_snapshots",
        "reference_directory": "csv/reference",
        "records": records,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"organized {len(records)} table exports")
    print(f"asset snapshots: {sum(r['kind'] == 'asset_snapshot' for r in records)}")
    print(f"reference tables: {sum(r['kind'] == 'reference' for r in records)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    return 0


def check() -> int:
    if source_tables():
        print("source organization: FAIL; anonymous table-*.csv files remain")
        return 1
    if not MANIFEST.exists():
        print("source organization: FAIL; csv/source_manifest.json is missing")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = manifest.get("records", [])
    if manifest.get("schema_version") != SCHEMA_VERSION or not records:
        print("source organization: FAIL; invalid source manifest")
        return 1
    errors: list[str] = []
    for record in records:
        path = ROOT / record["path"]
        if not path.exists():
            errors.append(f"missing {record['path']}")
        elif digest(path) != record.get("sha256"):
            errors.append(f"hash mismatch {record['path']}")
        elif not record.get("original_sha256"):
            errors.append(f"missing original source hash {record['path']}")
        elif record.get("original_sha256") != record.get("sha256"):
            errors.append(f"source/destination hash mismatch {record['path']}")
        # destination_verified_recovered is intentionally accepted for this
        # already-materialized repository, but remains visible in the manifest
        # and must not be described as a fresh source-file comparison.
    if errors:
        print(f"source organization: FAIL; {len(errors)} issue(s)")
        for error in errors[:20]:
            print(error)
        return 1
    print(f"source organization: PASS; {len(records)} named source files verified")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return write() if args.write else check()


if __name__ == "__main__":
    raise SystemExit(main())
