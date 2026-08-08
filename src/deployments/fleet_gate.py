"""No-spend preflight for the native deployment fleet.

It validates local package structure and emits the exact external checks still
required. It never invokes the Blocks CLI, network, registration, or tasks.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "blocks_deploy"
REQUIRED_FILES = ("agent-card.json", "handler.py", "trigger.py", "pyproject.toml", "deployment-metadata.json")


def inspect_fleet() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    projects = sorted(path for path in DEPLOY.iterdir() if path.is_dir() and (path / "pyproject.toml").exists())
    if len(projects) != 12:
        errors.append(f"expected 12 native projects, found {len(projects)}")
    for project in projects:
        for filename in REQUIRED_FILES:
            if not (project / filename).exists():
                errors.append(f"{project.name}: missing {filename}")
        card_path = project / "agent-card.json"
        metadata_path = project / "deployment-metadata.json"
        try:
            card = json.loads(card_path.read_text(encoding="utf-8"))
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            identity = card.get("identity", {})
            if identity.get("agentName") != project.name:
                errors.append(f"{project.name}: card identity does not match directory")
            if metadata.get("agent_name") != project.name:
                errors.append(f"{project.name}: deployment metadata agent_name does not match directory")
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{project.name}: invalid card or metadata: {error}")
    external = [
        "blocks check in every native project",
        "private registration and registry version verification",
        "provider runtime connectivity observation",
        "A2A grants and private invitation acceptance",
        "approved paid canary and billing reconciliation",
    ]
    return errors, external


def main() -> int:
    parser = argparse.ArgumentParser(description="No-spend native fleet preflight")
    parser.parse_args()
    errors, external = inspect_fleet()
    if errors:
        print("fleet gate: LOCAL PREFLIGHT FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("fleet gate: LOCAL PREFLIGHT READY")
    print("external gates still required:")
    for item in external:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
