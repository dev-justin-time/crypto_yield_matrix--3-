"""Safely trigger a private Blocks agent without hiding paid-task behavior.

Default behavior is ``--dry-run`` and never imports the Blocks SDK. A real
trigger requires both ``--live`` and ``--confirm-paid`` plus the explicit
``BLOCKS_API_KEY`` environment variable. This utility does not register,
publish, retry, or mutate deployment configuration.

Examples:
    python trigger_guarded.py --agent crypto_risk_analyst --dry-run
    python trigger_guarded.py --agent crypto_risk_analyst --live --confirm-paid \
      --request '{"question":"Analyze BTC","symbol":"BTC"}'
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import threading
from typing import Any

DEFAULT_REQUEST = {"question": "Smoke test: inspect BTC yield and downside context.", "symbol": "BTC", "source_file": "yield_data.csv"}


def parse_request(raw: str | None) -> dict[str, Any]:
    if not raw:
        return dict(DEFAULT_REQUEST)
    value = json.loads(raw)
    if not isinstance(value, dict) or not value.get("question"):
        raise ValueError("--request must be a JSON object with a non-empty question")
    return value


def dry_run(agent: str, request: dict[str, Any]) -> int:
    print("DRY RUN: no Blocks SDK import, network call, registration, or paid task.")
    print(json.dumps({"agent": agent, "request": request, "billing": "not dispatched"}, indent=2, sort_keys=True))
    return 0


def live_trigger(agent: str, request: dict[str, Any], timeout: int, client_factory: Any | None = None) -> int:
    if not os.environ.get("BLOCKS_API_KEY"):
        raise RuntimeError("BLOCKS_API_KEY is required for --live; no task was dispatched")
    try:
        from blocks_network import SendMessageRequestPart, create_task_client
    except ImportError as exc:
        raise RuntimeError("blocks-network is required for --live") from exc
    # The explicit positional mode is required: this utility is for paid
    # private canaries only and must not inherit the SDK's free default.
    client = (client_factory or create_task_client)("paid", api_key=os.environ["BLOCKS_API_KEY"])
    session = client.send_message(
        agent_name=agent,
        request_parts=[SendMessageRequestPart(part_id="request", text=json.dumps(request, separators=(",", ":")))],
    )
    done = threading.Event()
    terminal_state: str | None = None

    def progress(event: Any) -> None:
        print("[progress]", event.get("message") or event.get("progress") or "")

    def artifact(event: Any) -> None:
        reference = getattr(event, "artifact_ref", None) or getattr(event, "artifactRef", None)
        if reference is None:
            print("[artifact]", getattr(event, "raw", event))
        elif getattr(reference, "kind", None) == "inline" and reference.data:
            data = reference.data if isinstance(reference.data, bytes) else base64.b64decode(reference.data)
            print("[artifact]", data.decode("utf-8"))
        else:
            print("[artifact]", session.download_artifact(reference).data.decode("utf-8"))

    def terminal(event: Any) -> None:
        nonlocal terminal_state
        terminal_state = str(getattr(event, "state", "unknown"))
        print("[done]", terminal_state)
        done.set()

    session.on_progress(progress)
    session.on_artifact(artifact)
    session.on_terminal(terminal)
    try:
        if not done.wait(timeout=timeout):
            cancel = getattr(session, "cancel", None)
            if callable(cancel):
                cancel()
            raise TimeoutError(f"task did not complete within {timeout} seconds")
        if terminal_state != "completed":
            raise RuntimeError(f"private paid task ended in non-success state: {terminal_state}")
    finally:
        session.close()
        client.destroy()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--request", help="JSON request object")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--live", action="store_true", help="allow a real private Blocks request")
    parser.add_argument("--confirm-paid", action="store_true", help="explicitly acknowledge that --live may incur a paid task")
    parser.add_argument("--dry-run", action="store_true", help="explicit no-spend mode; also the default")
    args = parser.parse_args()
    request = parse_request(args.request)
    if not args.live or args.dry_run:
        return dry_run(args.agent, request)
    if not args.confirm_paid:
        raise SystemExit("Refusing live dispatch: add --confirm-paid to acknowledge the paid-task risk")
    print("WARNING: dispatching one real private Blocks task in billing_mode=paid may incur billing and use provider quota.")
    return live_trigger(args.agent, request, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
