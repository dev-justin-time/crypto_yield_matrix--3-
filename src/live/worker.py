"""24/7 supervisor loop for the live overlay.

Run with ``python live_worker.py`` or use ``docker-compose.live.yml``. The
worker is intentionally separate from Blocks task execution: a provider outage
cannot change the canonical research source or dispatch paid work.
"""
from __future__ import annotations

import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from src.live.collector import DEFAULT_CYCLE_SECONDS, DEFAULT_OUTPUT, DEFAULT_STATUS, LiveDataCollector, load_symbols, write_snapshot

ROOT = Path(__file__).resolve().parents[2]
DEPLOY_ROOT = ROOT / "blocks_deploy"
_STOP = False


def _stop(_signum: int, _frame: object) -> None:
    global _STOP
    _STOP = True


def _write_status(status: dict[str, object], path: Path = DEFAULT_STATUS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _mirror_snapshot(snapshot: dict[str, object]) -> int:
    """Mirror the same explicit overlay to native data-consuming deployments."""
    count = 0
    if not DEPLOY_ROOT.exists():
        return count
    for project in sorted(DEPLOY_ROOT.iterdir()):
        if not project.is_dir() or project.name == "crypto_yield_a2a_orchestrator":
            continue
        destination = project / "live_data" / "live_snapshot.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_snapshot(snapshot, destination)
        count += 1
    return count


def _read_previous_snapshot() -> dict[str, object]:
    if not DEFAULT_OUTPUT.exists():
        return {}
    try:
        value = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _merge_observations(previous: dict[str, object], current: dict[str, object], key: str, identity: str) -> None:
    previous_section = previous.get(key, {}) if isinstance(previous.get(key), dict) else {}
    current_section = current.get(key, {}) if isinstance(current.get(key), dict) else {}
    previous_items = previous_section.get(identity, {}) if isinstance(previous_section.get(identity), dict) else {}
    current_items = current_section.get(identity, {}) if isinstance(current_section.get(identity), dict) else {}
    merged = dict(previous_items)
    merged.update(current_items)
    for item_id, item in merged.items():
        if item_id not in current_items and isinstance(item, dict):
            retained = dict(item)
            retained["observation_status"] = "retained_from_previous_cycle"
            retained["retained_from"] = previous.get("generated_at")
            merged[item_id] = retained
    current_section[identity] = merged
    current_section["asset_count"] = len(merged) if identity == "assets" else current_section.get("asset_count", len(merged))
    current[key] = current_section


def merge_with_previous(previous: dict[str, object], current: dict[str, object]) -> dict[str, object]:
    """Preserve healthy observations during partial outages, but mark them old."""
    if not previous:
        return current
    merged = dict(current)
    _merge_observations(previous, merged, "market", "assets")
    # Chain and RPC arrays are keyed by chain and merged into maps temporarily.
    for section, list_key in (("defi", "chains"), ("blockchain", "observations")):
        old_section = previous.get(section, {}) if isinstance(previous.get(section), dict) else {}
        new_section = merged.get(section, {}) if isinstance(merged.get(section), dict) else {}
        old_rows = old_section.get(list_key, []) if isinstance(old_section.get(list_key), list) else []
        new_rows = new_section.get(list_key, []) if isinstance(new_section.get(list_key), list) else []
        by_chain = {str(row.get("chain")): row for row in old_rows if isinstance(row, dict) and row.get("chain")}
        by_chain.update({str(row.get("chain")): row for row in new_rows if isinstance(row, dict) and row.get("chain")})
        for chain, row in by_chain.items():
            if not any(isinstance(item, dict) and str(item.get("chain")) == chain for item in new_rows):
                row = dict(row)
                row["observation_status"] = "retained_from_previous_cycle"
                row["retained_from"] = previous.get("generated_at")
                by_chain[chain] = row
        new_section[list_key] = list(by_chain.values())
        new_section[f"{list_key[:-1]}_count"] = len(new_section[list_key])
        merged[section] = new_section
    current_errors = current.get("errors", []) if isinstance(current.get("errors"), list) else []
    if current_errors:
        merged["data_status"] = "live_overlay_degraded"
    return merged


def run_once(collector: LiveDataCollector, mirror: bool = True) -> dict[str, object]:
    started = time.monotonic()
    previous = _read_previous_snapshot()
    current_snapshot = collector.collect()
    current_observation_count = (
        int(current_snapshot.get("market", {}).get("asset_count", 0))
        + int(current_snapshot.get("defi", {}).get("chain_count", 0))
        + int(current_snapshot.get("blockchain", {}).get("observation_count", 0))
    )
    snapshot = merge_with_previous(previous, current_snapshot)
    # A successful cycle is one with at least one current market, chain, or RPC
    # observation. If every upstream failed, retain the prior snapshot on disk
    # and expose the failure in status rather than presenting an empty feed.
    market_section = snapshot.get("market", {}) if isinstance(snapshot.get("market"), dict) else {}
    defi_section = snapshot.get("defi", {}) if isinstance(snapshot.get("defi"), dict) else {}
    blockchain_section = snapshot.get("blockchain", {}) if isinstance(snapshot.get("blockchain"), dict) else {}
    observation_count = (
        int(market_section.get("asset_count", 0))
        + int(defi_section.get("chain_count", 0))
        + int(blockchain_section.get("observation_count", 0))
    )
    if observation_count > 0 or previous:
        write_snapshot(snapshot, DEFAULT_OUTPUT)
        mirrored = _mirror_snapshot(snapshot) if mirror else 0
        outcome = "updated"
    else:
        mirrored = 0
        outcome = "retained_previous_snapshot"
    current_fresh = current_observation_count > 0 and not snapshot.get("errors")
    status = {
        "worker": "crypto_yield_matrix_live_data",
        "status": "ok" if current_fresh else "degraded",
        "liveness": "running",
        "data_readiness": "fresh_observations" if current_fresh else "degraded" if observation_count > 0 else "no_fresh_observation",
        "last_cycle_at": snapshot["generated_at"],
        "last_outcome": outcome if current_observation_count > 0 else "retained_previous_snapshot",
        "observations": observation_count,
        "errors": len(snapshot.get("errors", [])),
        "deployment_mirrors": mirrored,
        "cycle_duration_ms": round((time.monotonic() - started) * 1000),
        "canonical_source_unchanged": "yield_data.csv",
        "providers": snapshot.get("provider_status", []),
        "current_observations": current_observation_count,
    }
    _write_status(status)
    return status


def main() -> None:
    cycle_seconds = max(30, float(os.getenv("LIVE_WORKER_CYCLE_SECONDS", DEFAULT_CYCLE_SECONDS)))
    timeout = max(3, float(os.getenv("LIVE_WORKER_TIMEOUT_SECONDS", "15")))
    mirror = os.getenv("LIVE_WORKER_MIRROR_DEPLOYMENTS", "1").lower() not in {"0", "false", "no"}
    collector = LiveDataCollector(load_symbols(), timeout=timeout)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    _write_status({"worker": "crypto_yield_matrix_live_data", "status": "starting", "liveness": "starting", "data_readiness": "unknown", "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "cycle_seconds": cycle_seconds})
    while not _STOP:
        try:
            run_once(collector, mirror=mirror)
        except Exception as error:  # Keep the supervisor alive on unexpected provider/parser errors.
            _write_status({"worker": "crypto_yield_matrix_live_data", "status": "degraded", "liveness": "running", "data_readiness": "no_fresh_observation", "last_outcome": "cycle_failed", "error": str(error)[:500], "canonical_source_unchanged": "yield_data.csv"})
        deadline = time.monotonic() + cycle_seconds
        while not _STOP and time.monotonic() < deadline:
            time.sleep(min(5.0, max(0.1, deadline - time.monotonic())))
    _write_status({"worker": "crypto_yield_matrix_live_data", "status": "stopped", "liveness": "stopped", "data_readiness": "unavailable", "stopped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "canonical_source_unchanged": "yield_data.csv"})


if __name__ == "__main__":
    main()
