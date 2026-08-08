"""Validate a release record without contacting Blocks or spending money."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "release_version", "commit_or_image_digest", "audit_date", "blocks_organization",
    "provider_registry_ids_and_versions", "billing_mode_and_price",
    "gateway_image_digest_and_sdk_version", "gateway_host_and_edge",
    "secret_manager_reference_and_last_rotation", "a2a_grants_verified_for",
    "provider_health_observation_window", "private_trigger_results", "paid_canary_task_ids",
    "paid_canary_max_approved_spend", "actual_task_count_and_spend", "rollback_result",
    "monitoring_dashboard_and_alert_owner", "incident_owner", "go_approver",
    "next_review_or_expiry_date",
)
EXPECTED_AGENTS = 12
EXPECTED_AGENT_NAMES = {
    "crypto_research_communications_agent", "crypto_risk_analyst", "crypto_yield_a2a_orchestrator",
    "data_provenance_auditor", "defi_liquidity_analyst", "feature_engineering_expert",
    "matrix_research_insights_agent", "model_validation_guardian", "portfolio_scenario_expert",
    "quant_forecasting_expert", "tokenomics_sustainability_expert", "yield_methodology_expert",
}
EXPECTED_A2A_GRANTS = 5
SPECIALISTS = {"data_provenance_auditor", "feature_engineering_expert", "crypto_risk_analyst", "defi_liquidity_analyst", "tokenomics_sustainability_expert"}
PLACEHOLDERS = {"", "todo", "tbd", "pending", "replace_me", "your-value", "unknown", "n/a"}


def template() -> dict[str, Any]:
    record = {field: "" for field in REQUIRED_FIELDS}
    record.update({"provider_registry_ids_and_versions": [], "a2a_grants_verified_for": [], "private_trigger_results": [], "paid_canary_task_ids": []})
    return record


def _text(value: Any) -> str:
    return str(value).strip().lower() if value is not None else ""


def _nonempty(value: Any) -> bool:
    if isinstance(value, str): return _text(value) not in PLACEHOLDERS
    if isinstance(value, list): return bool(value) and all(_nonempty(item) for item in value)
    if isinstance(value, dict): return bool(value) and all(_nonempty(item) for item in value.values())
    return value is not None


def _date(value: Any) -> bool:
    try: dt.date.fromisoformat(str(value)[:10]); return True
    except (TypeError, ValueError): return False


def _records(value: Any, field: str, keys: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list): return [f"{field} must be a list of objects"]
    for index, item in enumerate(value):
        if not isinstance(item, dict): errors.append(f"{field}[{index}] must be an object"); continue
        for key in keys:
            if not _nonempty(item.get(key)): errors.append(f"{field}[{index}] missing {key}")
    return errors


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record or not _nonempty(record[field]): errors.append(f"missing or placeholder release evidence: {field}")
    digest = str(record.get("commit_or_image_digest", ""))
    if digest and not re.fullmatch(r"(?:sha256:)?[0-9a-fA-F]{32,128}", digest): errors.append("commit_or_image_digest must be a commit hash or sha256 digest")
    for field in ("audit_date", "next_review_or_expiry_date"):
        if record.get(field) and not _date(record[field]): errors.append(f"{field} must be ISO date or timestamp")
    billing = _text(record.get("billing_mode_and_price"))
    if billing and ("paid" not in billing or "$" not in billing): errors.append("billing_mode_and_price must explicitly document paid billing and a price")
    registries = record.get("provider_registry_ids_and_versions")
    errors.extend(_records(registries, "provider_registry_ids_and_versions", ("agent_name", "registry_id", "version", "billing_mode")))
    if isinstance(registries, list):
        names = {str(item.get("agent_name")) for item in registries if isinstance(item, dict)}
        if len(registries) != EXPECTED_AGENTS or names != EXPECTED_AGENT_NAMES: errors.append("provider registry evidence must contain exactly the canonical 12 agent names")
        if any(_text(item.get("billing_mode")) != "paid" for item in registries if isinstance(item, dict)): errors.append("every provider registry record must state paid billing")
    grants = record.get("a2a_grants_verified_for")
    errors.extend(_records(grants, "a2a_grants_verified_for", ("specialist", "granted_to", "verified_at")))
    if isinstance(grants, list) and SPECIALISTS - {str(item.get("specialist")) for item in grants if isinstance(item, dict)}: errors.append("A2A evidence must cover all five required specialists")
    triggers = record.get("private_trigger_results")
    errors.extend(_records(triggers, "private_trigger_results", ("case", "agent", "terminal_state", "observed_at")))
    if isinstance(triggers, list):
        allowed_states = {"completed", "failed", "canceled", "timeout", "error"}
        if any(_text(item.get("terminal_state")) not in allowed_states for item in triggers if isinstance(item, dict)):
            errors.append("private trigger terminal_state contains an unsupported value")
        required_cases = {"valid", "invalid_input", "source_rejection", "forecast_gate", "timeout", "cancellation", "large_artifact", "partial_a2a"}
        observed_cases = {str(item.get("case")) for item in triggers if isinstance(item, dict)}
        if required_cases - observed_cases:
            errors.append("private trigger evidence must cover valid, invalid_input, source_rejection, forecast_gate, timeout, cancellation, large_artifact, and partial_a2a")
    canary = record.get("paid_canary_task_ids")
    if not isinstance(canary, list) or not canary or any(not re.fullmatch(r"[A-Za-z0-9_.:-]{4,128}", str(item)) for item in canary): errors.append("paid_canary_task_ids must contain valid observed task IDs")
    if not isinstance(record.get("actual_task_count_and_spend"), dict): errors.append("actual_task_count_and_spend must be an object with task_count and spend_usd")
    else:
        actual = record["actual_task_count_and_spend"]
        if not isinstance(actual.get("task_count"), int) or actual["task_count"] < 1 or not isinstance(actual.get("spend_usd"), (int, float)) or actual["spend_usd"] < 0: errors.append("actual_task_count_and_spend has invalid numeric values")
    approved = record.get("paid_canary_max_approved_spend")
    if not isinstance(approved, (int, float)) or approved <= 0: errors.append("paid_canary_max_approved_spend must be a positive number")
    elif isinstance(record.get("actual_task_count_and_spend"), dict) and isinstance(record["actual_task_count_and_spend"].get("spend_usd"), (int, float)) and record["actual_task_count_and_spend"]["spend_usd"] > approved:
        errors.append("actual spend exceeds the approved paid-canary ceiling")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release evidence without network or paid tasks")
    parser.add_argument("--record", type=Path); parser.add_argument("--template", action="store_true")
    args = parser.parse_args()
    if args.template: print(json.dumps(template(), indent=2)); return 0
    if not args.record: parser.error("use --record FILE or --template")
    try: record = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: print(f"release gate: unable to read JSON record: {error}", file=sys.stderr); return 2
    if not isinstance(record, dict): print("release gate: record must be a JSON object", file=sys.stderr); return 2
    errors = validate_record(record)
    if errors:
        print("release gate: INCOMPLETE"); print("\n".join(f"- {error}" for error in errors)); return 1
    print("release gate: evidence record is complete for operator review")
    print("warning: this tool does not independently prove live Blocks, TLS, secrets, monitoring, permissions, or billing")
    return 0


if __name__ == "__main__": raise SystemExit(main())
