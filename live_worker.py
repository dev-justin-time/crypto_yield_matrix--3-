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

from live_data import DEFAULT_CYCLE_SECONDS, DEFAULT_OUTPUT, DEFAULT_STATUS, LiveDataCollector, load_symbols, write_snapshot

ROOT = Path(__file__).resolve().parent
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


def run_once(collector: LiveDataCollector, mirror: bool = True) -> dict[str, object]:
    started = time.monotonic()
    snapshot = collector.collect()
    # A successful cycle is one with at least one current market, chain, or RPC
    # observation. If every upstream failed, retain the prior snapshot on disk
    # and expose the failure in status rather than presenting an empty feed.
    observation_count = (
        int(snapshot["market"]["asset_count"])
        + int(snapshot["defi"]["chain_count"])
        + int(snapshot["blockchain"]["observation_count"])
    )
    if observation_count > 0:
        write_snapshot(snapshot, DEFAULT_OUTPUT)
        mirrored = _mirror_snapshot(snapshot) if mirror else 0
        outcome = "updated"
    else:
        mirrored = 0
        outcome = "retained_previous_snapshot"
    status = {
        "worker": "crypto_yield_matrix_live_data",
        "status": "ok" if observation_count > 0 else "degraded",
        "last_cycle_at": snapshot["generated_at"],
        "last_outcome": outcome,
        "observations": observation_count,
        "errors": len(snapshot.get("errors", [])),
        "deployment_mirrors": mirrored,
        "cycle_duration_ms": round((time.monotonic() - started) * 1000),
        "canonical_source_unchanged": "yield_data.csv",
        "providers": snapshot.get("provider_status", []),
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
    _write_status({"worker": "crypto_yield_matrix_live_data", "status": "starting", "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "cycle_seconds": cycle_seconds})
    while not _STOP:
        try:
            run_once(collector, mirror=mirror)
        except Exception as error:  # Keep the supervisor alive on unexpected provider/parser errors.
            _write_status({"worker": "crypto_yield_matrix_live_data", "status": "degraded", "last_outcome": "cycle_failed", "error": str(error)[:500], "canonical_source_unchanged": "yield_data.csv"})
        deadline = time.monotonic() + cycle_seconds
        while not _STOP and time.monotonic() < deadline:
            time.sleep(min(5.0, max(0.1, deadline - time.monotonic())))
    _write_status({"worker": "crypto_yield_matrix_live_data", "status": "stopped", "stopped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "canonical_source_unchanged": "yield_data.csv"})


if __name__ == "__main__":
    main()
