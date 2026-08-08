"""Evaluate live-worker liveness separately from data readiness.

Usage:
    python live_readiness.py [path/to/worker_status.json]

Exit status is non-zero when the worker is not running, the cycle is too old,
or no fresh observations are available. This utility never contacts providers.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.live.collector import DEFAULT_STALE_AFTER_SECONDS, DEFAULT_STATUS


def _age_seconds(value: Any, now: float | None = None) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError, OverflowError):
        return None
    return (time.time() if now is None else now) - timestamp


def evaluate_status(status: dict[str, Any], now: float | None = None, max_cycle_age: float = DEFAULT_STALE_AFTER_SECONDS + 300) -> dict[str, Any]:
    age = _age_seconds(status.get("last_cycle_at"), now)
    liveness = status.get("liveness")
    readiness = status.get("data_readiness")
    live_ok = liveness == "running" and age is not None and 0 <= age <= max_cycle_age
    try:
        current_observations = int(status.get("current_observations", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        current_observations = 0
    data_ok = readiness == "fresh_observations" and current_observations > 0
    return {
        "liveness_ok": live_ok,
        "data_ready": data_ok,
        "status": "ready" if live_ok and data_ok else "degraded" if live_ok else "unavailable",
        "last_cycle_age_seconds": round(age, 3) if age is not None else None,
        "liveness": liveness or "unknown",
        "data_readiness": readiness or "unknown",
        "alerts": (["worker_liveness_failed"] if not live_ok else []) + (["no_fresh_observation_or_degraded_data"] if not data_ok else []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_STATUS)
    args = parser.parse_args()
    try:
        status = json.loads(args.path.read_text(encoding="utf-8"))
        if not isinstance(status, dict):
            raise ValueError("status must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        result = {"status": "unavailable", "liveness_ok": False, "data_ready": False, "alerts": ["worker_status_unreadable"], "error": str(error)}
        print(json.dumps(result, indent=2))
        return 2
    result = evaluate_status(status)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
