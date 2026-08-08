"""Synchronize and verify deterministic source mirrors for native deployments.

Usage:
    python sync_deployments.py --write   # copy approved source mirrors
    python sync_deployments.py --check   # verify without changing files

This tool never mirrors credentials, live snapshots, or native deployment cards.
The A2A orchestrator is intentionally excluded because it has a custom runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPLOY_ROOT = ROOT / "blocks_deploy"
MANIFEST = ROOT / "deployment_mirror_manifest.json"

SOURCE_FILES = (
    "blocks_agents/__init__.py",
    "blocks_agents/loader.py",
    "blocks_agents/README.md",
    "blocks_agents/agent_cards.json",
    "blocks_agents/crypto_research_communications_agent.json",
    "blocks_agents/crypto_risk_analyst.json",
    "blocks_agents/data_provenance_auditor.json",
    "blocks_agents/defi_liquidity_analyst.json",
    "blocks_agents/feature_engineering_expert.json",
    "blocks_agents/matrix_research_insights_agent.json",
    "blocks_agents/model_validation_guardian.json",
    "blocks_agents/portfolio_scenario_expert.json",
    "blocks_agents/quant_forecasting_expert.json",
    "blocks_agents/tokenomics_sustainability_expert.json",
    "blocks_agents/yield_methodology_expert.json",
    "blocks_agents/handlers/__init__.py",
    "blocks_agents/handlers/__main__.py",
    "blocks_agents/handlers/common.py",
    "blocks_agents/handlers/crypto_research_communications_agent.py",
    "blocks_agents/handlers/crypto_risk_analyst.py",
    "blocks_agents/handlers/data_provenance_auditor.py",
    "blocks_agents/handlers/defi_liquidity_analyst.py",
    "blocks_agents/handlers/feature_engineering_expert.py",
    "blocks_agents/handlers/matrix_research_insights_agent.py",
    "blocks_agents/handlers/model_validation_guardian.py",
    "blocks_agents/handlers/portfolio_scenario_expert.py",
    "blocks_agents/handlers/quant_forecasting_expert.py",
    "blocks_agents/handlers/tokenomics_sustainability_expert.py",
    "blocks_agents/handlers/yield_methodology_expert.py",
    "DATA_DICTIONARY.md",
    "validate.md",
    "yield_data.csv",
    "asset_catalog.csv",
)

# Generated one-row-per-asset evidence exports are part of the reproducible
# package, while live snapshots remain an operational overlay and are excluded.
SOURCE_GLOBS = ("csv/assets/*.csv", "csv/quotes/*.csv")


def deployment_projects() -> list[Path]:
    return [
        path
        for path in sorted(DEPLOY_ROOT.iterdir())
        if path.is_dir() and path.name != "crypto_yield_a2a_orchestrator"
    ]


def source_paths() -> list[Path]:
    paths = [ROOT / relative for relative in SOURCE_FILES]
    for pattern in SOURCE_GLOBS:
        paths.extend(sorted(ROOT.glob(pattern)))
    return sorted(dict.fromkeys(paths), key=lambda path: path.relative_to(ROOT).as_posix())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def expected_targets(source: Path) -> list[Path]:
    rel = source.relative_to(ROOT)
    return [project / rel for project in deployment_projects()]


def records() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for source in source_paths():
        if not source.is_file():
            raise FileNotFoundError(source)
        result.append({
            "source": relative(source),
            "sha256": digest(source),
            "targets": [target.relative_to(ROOT).as_posix() for target in expected_targets(source)],
        })
    return result


def check() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    missing: list[dict[str, str]] = []
    mismatched: list[dict[str, str]] = []
    for record in records():
        source = ROOT / str(record["source"])
        expected = str(record["sha256"])
        for target_name in record["targets"]:  # type: ignore[union-attr]
            target = ROOT / str(target_name)
            if not target.exists():
                missing.append({"source": relative(source), "target": target_name})
            elif digest(target) != expected:
                mismatched.append({"source": relative(source), "target": target_name})
    return missing, mismatched


def write_mirrors() -> None:
    for record in records():
        source = ROOT / str(record["source"])
        for target_name in record["targets"]:  # type: ignore[union-attr]
            target = ROOT / str(target_name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    MANIFEST.write_text(
        json.dumps({
            "schema_version": 1,
            "policy": "deterministic source mirrors; credentials and live snapshots excluded",
            "excluded_projects": ["crypto_yield_a2a_orchestrator"],
            "deployments": [project.name for project in deployment_projects()],
            "files": records(),
        }, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write deterministic mirrors and the manifest")
    mode.add_argument("--check", action="store_true", help="check mirrors without modifying files")
    args = parser.parse_args()
    if args.write:
        write_mirrors()
        print(f"wrote {len(records())} source files to {len(deployment_projects())} deployments")
        print(f"manifest: {MANIFEST.relative_to(ROOT)}")
        return 0
    missing, mismatched = check()
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("files") != records():
            mismatched.append({"source": "deployment_mirror_manifest.json", "target": "generated manifest is stale"})
    else:
        missing.append({"source": "deployment_mirror_manifest.json", "target": "deployment_mirror_manifest.json"})
    print(f"mirror check: {len(missing)} missing, {len(mismatched)} mismatched")
    if missing or mismatched:
        for item in (missing + mismatched)[:20]:
            print(json.dumps(item, sort_keys=True))
        return 1
    print("mirror check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
