"""Materialize native Blocks adapters from the local agent-card source of truth.

The standard specialist adapters are intentionally thin: they import the
source handler and let Blocks own transport/billing. The A2A orchestrator has a
custom adapter and is never overwritten by this generator.

Usage:
    python generate_deployments.py --write
    python generate_deployments.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS_ROOT = ROOT / "blocks_agents"
DEPLOY_ROOT = ROOT / "blocks_deploy"
INDEX = CARDS_ROOT / "agent_cards.json"
GENERATOR_VERSION = "1"
ORCHESTRATOR = "crypto_yield_a2a_orchestrator"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indexed_cards() -> list[tuple[str, dict, Path]]:
    index = read_json(INDEX)
    result = []
    for filename in index["agents"]:
        path = CARDS_ROOT / filename
        card = read_json(path)
        result.append((card["identity"]["agentName"], card, path))
    return result


def wrapper(agent_name: str) -> str:
    return f'''"""Generated native Blocks adapter for {agent_name}.\n\nSource card: blocks_agents/{agent_name}.json\nDo not add business logic here; edit the source handler instead.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Optional\n\nfrom blocks_network import StartTaskMessage, TaskContext\nfrom blocks_agents.handlers.{agent_name} import handler as local_handler\n\n\ndef handler(task: StartTaskMessage, ctx: Optional[TaskContext] = None) -> dict:\n    return local_handler(task, ctx)\n'''


def stable_card_contract(card: dict) -> dict:
    """Fields that must remain aligned between source and native cards.

    Native cards may add transport-specific runtime limits and input fields, so
    those are deliberately not compared here. Identity, capability, and tag
    drift changes what users are being promised and must fail generation.
    """
    return {
        "identity": {
            key: card.get("identity", {}).get(key)
            for key in ("agentName", "displayName", "description", "provider")
        },
        "taskKinds": card.get("capabilities", {}).get("taskKinds", []),
        "tags": card.get("tags", []),
    }


def card_consistency_errors(source_card: dict, native_card: dict, agent_name: str) -> list[str]:
    errors = []
    if stable_card_contract(source_card) != stable_card_contract(native_card):
        errors.append(f"native card stable contract differs from root card: {agent_name}")
    if native_card.get("identity", {}).get("agentName") != agent_name:
        errors.append(f"native card identity does not match source card: {agent_name}")
    runtime = native_card.get("runtime", {})
    if runtime.get("handler") != "./handler.py" or runtime.get("handlerExport") != "handler":
        errors.append(f"native card runtime must expose ./handler.py:handler: {agent_name}")
    for field in ("concurrency", "expectedInstances", "maxPendingBacklog", "maxRunningTimeSec"):
        value = runtime.get(field)
        if not isinstance(value, int) or value < 1:
            errors.append(f"native card runtime.{field} must be a positive integer: {agent_name}")
    return errors


def metadata(agent_name: str, card: dict, card_path: Path, project: Path, native_card: dict) -> dict:
    return {
        "schema_version": 1,
        "generated_by": "generate_deployments.py",
        "generator_version": GENERATOR_VERSION,
        "agent_name": agent_name,
        "source_card": card_path.relative_to(ROOT).as_posix(),
        "source_card_sha256": sha256(card_path),
        "source_card_version": card.get("identity", {}).get("version"),
        "native_card_version": native_card.get("identity", {}).get("version"),
        "version_policy": "Root card version describes local source semantics; native card version describes the registered package. Native version changes require blocks check and a controlled canary.",
        "runtime_policy": "Native runtime limits are package deployment policy and must remain positive, bounded, and explicitly reviewed; the adapter must remain ./handler.py:handler.",
        "source_handler": card["runtime"]["handler"],
        "deployment_project": project.name,
        "deployment_card": f"{project.name}/agent-card.json",
        "deployment_card_sha256": sha256(project / "agent-card.json"),
        "card_contract": stable_card_contract(native_card),
        "native_adapter": {
            "path": f"{project.name}/handler.py",
            "kind": "delegating_standard_handler",
            "generated": agent_name != ORCHESTRATOR,
        },
        "blocks_validation": {
            "required": True,
            "executed_by_generator": False,
            "command": "blocks check",
            "note": "Requires the official Blocks CLI and project credentials; never run as part of no-spend local generation.",
        },
    }


def expected() -> dict[Path, str | dict]:
    outputs: dict[Path, str | dict] = {}
    projects = {path.name: path for path in DEPLOY_ROOT.iterdir() if path.is_dir()}
    for agent_name, card, card_path in indexed_cards():
        project = projects.get(agent_name)
        if project is None:
            raise FileNotFoundError(f"missing deployment project for {agent_name}")
        native_card_path = project / "agent-card.json"
        native_card = read_json(native_card_path)
        errors = card_consistency_errors(card, native_card, agent_name)
        if errors:
            raise ValueError("; ".join(errors))
        outputs[project / "handler.py"] = wrapper(agent_name)
        outputs[project / "deployment-metadata.json"] = metadata(agent_name, card, card_path, project, native_card)

    # The orchestrator has custom A2A behavior and is not derived from a root
    # specialist card, but it still receives deterministic metadata from its
    # native card and is included in the packaging contract.
    orchestrator_project = DEPLOY_ROOT / ORCHESTRATOR
    if not orchestrator_project.exists():
        raise FileNotFoundError(orchestrator_project)
    orchestrator_card_path = orchestrator_project / "agent-card.json"
    orchestrator_card = read_json(orchestrator_card_path)
    outputs[orchestrator_project / "deployment-metadata.json"] = metadata(
        ORCHESTRATOR, orchestrator_card, orchestrator_card_path, orchestrator_project, orchestrator_card,
    )
    return outputs


def check() -> list[str]:
    errors = []
    try:
        outputs = expected()
    except (FileNotFoundError, ValueError) as exc:
        return [str(exc)]
    for path, expected_value in outputs.items():
        if not path.exists():
            errors.append(f"missing generated file: {path.relative_to(ROOT)}")
        else:
            actual = path.read_text(encoding="utf-8") if isinstance(expected_value, str) else read_json(path)
            if actual != expected_value:
                errors.append(f"generated file differs: {path.relative_to(ROOT)}")
    return errors


def write() -> None:
    for path, content in expected().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8", newline="\n")
        else:
            path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
        print(f"generated {len(expected())} adapter/metadata files")
        return 0
    errors = check()
    print(f"generated output check: {len(errors)} differences")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
