"""A2A orchestrator for the Crypto Yield Matrix specialists."""

from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event
from typing import Any, Optional

from blocks_network import SendMessageRequestPart, StartTaskMessage, TaskContext

SPECIALISTS = (
    "data_provenance_auditor",
    "feature_engineering_expert",
    "crypto_risk_analyst",
    "defi_liquidity_analyst",
    "tokenomics_sustainability_expert",
)
SUBTASK_TIMEOUT_SECONDS = 30


def request_payload(task: StartTaskMessage) -> dict[str, Any]:
    for part in task.request_parts:
        if part.text is None:
            continue
        text = str(part.text)
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return {"question": text}
        return value if isinstance(value, dict) else {"question": text}
    return {}


def decode_artifact(event: Any) -> Any:
    reference = getattr(event, "artifact_ref", None) or getattr(event, "artifactRef", None)
    if reference is None:
        return None
    if getattr(reference, "kind", None) == "inline" and reference.data:
        raw = reference.data if isinstance(reference.data, bytes) else base64.b64decode(reference.data)
    else:
        raise RuntimeError("non-inline artifact requires session download")
    text = raw.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def execute_subtask(task_client: Any, agent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        session = task_client.send_message(
            agent_name=agent_name,
            request_parts=[SendMessageRequestPart(part_id="request", text=json.dumps(payload))],
        )
    except Exception as exc:
        return {"agent": agent_name, "status": "failed", "error": str(exc)}

    finished = Event()
    state: dict[str, Any] = {"terminal": None, "artifact": None}

    def on_artifact(event: Any) -> None:
        reference = getattr(event, "artifact_ref", None) or getattr(event, "artifactRef", None)
        if reference is not None and getattr(reference, "kind", None) != "inline":
            downloaded = session.download_artifact(reference)
            raw = getattr(downloaded, "data", downloaded)
            text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            try:
                state["artifact"] = json.loads(text)
            except json.JSONDecodeError:
                state["artifact"] = text
        else:
            state["artifact"] = decode_artifact(event)

    def on_terminal(event: Any) -> None:
        state["terminal"] = getattr(event, "state", None)
        finished.set()

    session.on_artifact(on_artifact)
    session.on_terminal(on_terminal)
    try:
        if not finished.wait(timeout=SUBTASK_TIMEOUT_SECONDS):
            return {"agent": agent_name, "status": "timeout", "error": "specialist timed out"}
        if state["terminal"] == "completed":
            return {"agent": agent_name, "status": "completed", "artifact": state["artifact"]}
        return {"agent": agent_name, "status": "failed", "error": state["terminal"] or "unknown terminal state", "artifact": state["artifact"]}
    finally:
        session.close()


def merge_results(results: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    successful = [item for item in results if item["status"] == "completed"]
    failed = [item for item in results if item["status"] != "completed"]
    statuses: list[str] = []
    findings: list[Any] = []
    assumptions: list[str] = []
    limitations: list[str] = []
    context_files: set[str] = set()
    source_files: set[str] = set()

    for item in successful:
        artifact = item.get("artifact")
        if not isinstance(artifact, dict):
            findings.append({"agent": item["agent"], "status": "WARNING", "issue": "non-object artifact"})
            continue
        statuses.append(str(artifact.get("status", "WARNING")))
        findings.extend(artifact.get("findings", []))
        assumptions.extend(artifact.get("assumptions", []))
        limitations.extend(artifact.get("limitations", []))
        provenance = artifact.get("provenance", {})
        if provenance.get("source_file"):
            source_files.add(provenance["source_file"])
        context_files.update(provenance.get("context_files", []))

    if failed or "FAIL" in statuses:
        status = "FAIL" if len(failed) > len(SPECIALISTS) // 2 or "FAIL" in statuses else "WARNING"
    elif "WARNING" in statuses:
        status = "WARNING"
    else:
        status = "PASS"

    if failed:
        findings.append({"agent": "crypto_yield_a2a_orchestrator", "status": "WARNING", "partial_failures": failed})
    return {
        "agent": "crypto_yield_a2a_orchestrator",
        "status": status,
        "summary": f"Merged {len(successful)} of {len(results)} specialist analyses for {payload.get('symbol') or 'the requested scope'}.",
        "findings": findings,
        "assumptions": assumptions,
        "limitations": list(dict.fromkeys(limitations + [
            "Specialists are private Blocks agents and may be unavailable or permission-denied.",
            "This merged report is research decision support, not financial advice.",
        ])),
        "provenance": {
            "mode": "blocks_a2a_read_only",
            "source_file": next(iter(source_files), payload.get("source_file", "yield_data.csv")),
            "context_files": sorted(context_files),
            "specialists": list(SPECIALISTS),
        },
    }


def handler(task: StartTaskMessage, ctx: Optional[TaskContext] = None) -> dict:
    task_client = getattr(ctx, "task_client", None) or getattr(ctx, "taskClient", None) if ctx else None
    if task_client is None:
        raise RuntimeError("A2A orchestration requires TaskContext.task_client")
    payload = request_payload(task)
    if ctx is not None:
        ctx.report_status("Dispatching specialist analyses in parallel...")
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(SPECIALISTS)) as executor:
        futures = [executor.submit(execute_subtask, task_client, name, payload) for name in SPECIALISTS]
        for future in as_completed(futures):
            results.append(future.result())
    if ctx is not None:
        ctx.report_status("Merging specialist artifacts...")
    merged = merge_results(results, payload)
    return {"artifacts": [{"data": json.dumps(merged, indent=2), "mimeType": "application/json"}]}
