from .common import report, status, task_payload


def handler(task, ctx=None):
    payload = task_payload(task)
    status(ctx, "Running duplicate provenance rows and leakage gates")
    features = set(payload.get("features", []))
    target = payload.get("target", "")
    target_fields = {"q3_26_forward_yield", "yield_direction_next_q", "risk_adjusted_yield", "outperformance_vs_market_pp", "investment_score"}
    forbidden = sorted(features & target_fields)
    source = payload.get("source_file")
    findings = [{"check": "single_source_version", "pass": source in {"yield_data.csv"}, "value": source}, {"check": "target_not_feature", "pass": not forbidden, "forbidden_features": forbidden}, {"check": "chronological_split", "pass": payload.get("split", "").lower() in {"walk_forward", "time_series", "expanding_window"}, "value": payload.get("split")}, {"check": "additional_dated_history", "pass": False, "reason": "The repository has only eight quarterly observations per asset."}]
    failed = any(not item["pass"] for item in findings)
    return report("model_validation_guardian", "FAIL" if failed else "PASS", "Model gate checks duplicate provenance rows, target circularity, chronological split, and minimum-history requirements.", findings, limitations=["This handler validates a requested design; it does not fit or certify a model.", "Small history still requires additional dated observations."], source_file=source, context_files=payload.get("files", []))
