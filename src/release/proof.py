"""Generate a reproducible final proof record without external or paid operations.

The default command runs only local, no-network validation commands and records
all stdout/stderr. It never runs Blocks registration, native ``blocks check``,
provider endpoints, A2A calls, or paid tasks. Those gates remain explicit
operator-populated evidence fields in the generated JSON.

Usage:
    python generate_proof_record.py --output proof_record.local.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "final-proof-record-1"


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_command(command: list[str], cwd: Path = ROOT) -> dict[str, Any]:
    executable = command[0]
    if os.name == "nt" and executable == "npm":
        executable = "npm.cmd"
    actual_command = [executable, *command[1:]]
    try:
        completed = subprocess.run(
            actual_command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except OSError as error:
        exit_code = 127
        stdout = ""
        stderr = f"{type(error).__name__}: {error}"
    return {
        "command": " ".join(command),
        "cwd": cwd.relative_to(ROOT).as_posix() if cwd != ROOT else ".",
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "external_or_paid": False,
    }


def git_status() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, text=True,
        capture_output=True, check=False, encoding="utf-8", errors="replace",
    )
    return [line for line in result.stdout.splitlines() if line]


def git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        capture_output=True, check=False, encoding="utf-8", errors="replace",
    )
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def python_manifests() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted((ROOT / "blocks_deploy").glob("*/pyproject.toml")):
        text = path.read_text(encoding="utf-8")
        pins = re.findall(r"blocks-network==([^\" ]+)", text)
        result.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
            "blocks_network_pins": pins,
        })
    return result


def node_dependencies() -> dict[str, Any]:
    package_path = ROOT / "crypto_yield_matrix_node_gateway" / "package.json"
    lock_path = ROOT / "crypto_yield_matrix_node_gateway" / "package-lock.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    return {
        "package_json_sha256": sha256(package_path),
        "package_lock_sha256": sha256(lock_path),
        "declared_sdk": package.get("dependencies", {}).get("@blocks-network/sdk"),
        "lock_root_sdk": lock.get("packages", {}).get("", {}).get("dependencies", {}).get("@blocks-network/sdk"),
        "lock_resolved_sdk": lock.get("packages", {}).get("node_modules/@blocks-network/sdk", {}).get("version"),
    }


def card_evidence() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for path in sorted((ROOT / "blocks_deploy").glob("*/agent-card.json")):
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
            identity = card.get("identity", {})
            name = identity.get("agentName") or path.parent.name
            version = identity.get("version")
        except (OSError, json.JSONDecodeError):
            name, version = path.parent.name, None
        cards.append({
            "agent_name": name,
            "card_path": path.relative_to(ROOT).as_posix(),
            "card_sha256": sha256(path),
            "card_version": version,
            "registry_identifier": "REQUIRED_EXTERNAL_EVIDENCE",
        })
    return cards


def _remove_fixture_files() -> None:
    for generated in (ROOT / "proof-record-worker-status.json", ROOT / "proof-record-canary.json"):
        try:
            generated.unlink()
        except FileNotFoundError:
            pass


def local_commands() -> list[dict[str, Any]]:
    # Remove leftovers from an interrupted prior run before collecting evidence.
    _remove_fixture_files()
    worker_fixture = ROOT / "proof-record-worker-status.json"
    worker_fixture.write_text(json.dumps({
        "worker": "proof-record-fixture",
        "liveness": "running",
        "data_readiness": "fresh_observations",
        "last_cycle_at": utc_now(),
        "current_observations": 1,
    }) + "\n", encoding="utf-8")
    commands: list[tuple[list[str], Path]] = [
        ([sys.executable, "-m", "py_compile", "live_data.py", "live_worker.py", "live_canary.py", "live_readiness.py", "test_live_data.py", "test_asset_sources.py", "organize_csv_sources.py", "build_asset_catalog.py", "sync_deployments.py", "generate_deployments.py"], ROOT),
        ([sys.executable, "organize_csv_sources.py", "--check"], ROOT),
        ([sys.executable, "build_asset_catalog.py"], ROOT),
        ([sys.executable, "sync_deployments.py", "--check"], ROOT),
        ([sys.executable, "generate_deployments.py", "--check"], ROOT),
        ([sys.executable, "run_live_tests.py"], ROOT),
        ([sys.executable, "test_asset_sources.py"], ROOT),
        ([sys.executable, "live_canary.py", "--fixture", "--output", "proof-record-canary.json"], ROOT),
        ([sys.executable, "live_readiness.py", worker_fixture.name], ROOT),
        ([sys.executable, "test_packaging.py"], ROOT),
        ([sys.executable, "audit_csv.py"], ROOT),
        (["node", "--check", "matrix.js"], ROOT),
        ([sys.executable, "-m", "pip", "check"], ROOT),
        (["npm", "run", "check"], ROOT / "crypto_yield_matrix_node_gateway"),
        (["npm", "run", "smoke"], ROOT / "crypto_yield_matrix_node_gateway"),
        (["npm", "run", "resilience"], ROOT / "crypto_yield_matrix_node_gateway"),
        (["npm", "run", "llm-smoke"], ROOT / "crypto_yield_matrix_node_gateway"),
        (["git", "diff", "--check"], ROOT),
    ]
    try:
        return [run_command(command, cwd) for command, cwd in commands]
    finally:
        _remove_fixture_files()


def build_record() -> dict[str, Any]:
    commands = local_commands()
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "local_reproducible_proof_record",
        "generated_at": utc_now(),
        "policy": "Local no-network evidence only; external and paid gates are never inferred from this record.",
        "repository": {
            "commit_sha": git_sha(),
            "working_tree_status": git_status(),
            "dirty": bool(git_status()),
        },
        "runtime": {
            "python": platform.python_version(),
            "node": run_command(["node", "--version"]),
            "npm": run_command(["npm", "--version"]),
            "platform": platform.platform(),
        },
        "dependencies": {
            "python_manifests": python_manifests(),
            "native_lockfiles": {
                "status": "NO_NATIVE_LOCKFILES_DECLARED",
                "paths": [],
                "note": "Native deployments pin blocks-network in pyproject.toml; no per-project Python lockfiles are present in this repository.",
            },
            "node": node_dependencies(),
            "deployment_mirror_manifest_sha256": sha256(ROOT / "deployment_mirror_manifest.json"),
            "vulnerability_and_licence_review": {
                "status": "NOT_RUN_APPROVED_TOOLING_UNAVAILABLE",
                "required_tools": ["approved organization vulnerability scanner", "approved license scanner"],
                "pip_check_is_not_a_vulnerability_or_license_scan": True,
            },
        },
        "local_commands": commands,
        "local_command_scope": "The commands listed here are the generator's reproducible local no-spend suite; prior shell commands and external operator evidence are not inferred.",
        "local_command_summary": {
            "commands": len(commands),
            "passed": sum(item["exit_code"] == 0 for item in commands),
            "failed": sum(item["exit_code"] != 0 for item in commands),
        },
        "native_cards": card_evidence(),
        "external_evidence_required": {
            "native_blocks_check": {
                "status": "NOT_RUN_BLOCKS_CLI_UNAVAILABLE_OR_EXTERNAL_RELEASE_ENV_REQUIRED",
                "projects": [p.name for p in sorted((ROOT / "blocks_deploy").iterdir()) if p.is_dir()],
                "command": "blocks check",
                "results": "OPERATOR_MUST_ATTACH_OUTPUT_PER_PROJECT",
            },
            "private_registry_and_card_identifiers": {
                "status": "REQUIRED_EXTERNAL_EVIDENCE",
                "records": "Populate native_cards[*].registry_identifier and attach registry/card output.",
            },
            "provider_canary": {
                "fixture_status": "LOCAL_FIXTURE_ONLY",
                "live_status": "REQUIRED_EXTERNAL_EVIDENCE",
                "required_fields": ["run timestamps", "provider", "endpoint", "HTTP status", "selected rate-limit headers", "schema result", "sanitized error", "terms/attribution review date"],
            },
            "live_a2a_permissions": {
                "status": "REQUIRED_EXTERNAL_EVIDENCE",
                "required_fields": ["specialist", "orchestrator identity", "grant/invitation state", "verified_at", "terminal/artifact evidence"],
            },
            "paid_canary_and_rollback": {
                "status": "REQUIRED_OWNER_APPROVAL_AND_EXTERNAL_EVIDENCE",
                "approved_budget_usd": "OPERATOR_MUST_POPULATE",
                "task_ids": "OPERATOR_MUST_POPULATE",
                "billing_reconciliation": "OPERATOR_MUST_ATTACH",
                "rollback_owner": "OPERATOR_MUST_POPULATE",
                "rollback_result": "OPERATOR_MUST_ATTACH",
            },
        },
        "remediation_order": [
            "Keep generated adapter and SHA-256 mirror checks required in CI.",
            "Pin SDK dependencies and maintain a lockfile/version policy.",
            "Run malformed/stale live snapshot checks in CI.",
            "Deploy and verify shared live-snapshot delivery before exposing live context to paid agents.",
            "Run a private, terms-reviewed, budgeted provider and Blocks canary.",
            "Deploy centralized observability, readiness alerts, and aggregate budget controls.",
            "Reassess public/unattended paid production only after all external evidence is independently reviewable.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "proof_record.local.json")
    args = parser.parse_args()
    record = build_record()
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(json.dumps(record["local_command_summary"], indent=2))
    return 0 if record["local_command_summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
