from .common import YIELD_SOURCES, report, status, task_payload


def handler(task, ctx=None):
    payload = task_payload(task)
    source = payload.get("source_file") or "yield_data.csv"
    if source not in YIELD_SOURCES:
        raise ValueError(f"source_file must be one of {sorted(YIELD_SOURCES)}")
    status(ctx, "Checking forecast readiness and leakage gates")
    return report("quant_forecasting_expert", "FAIL", "Forecast execution is blocked for production use until source identity is resolved and additional dated observations are added.", [{"check": "source_selected", "pass": payload.get("source_file") in {"yield_data.csv", "yield_data1.csv"}}, {"check": "additional_history", "pass": False, "reason": "Current project has eight quarterly observations per asset."}, {"check": "walk_forward_validation", "pass": False, "reason": "No fitted model or independent future outcomes were supplied."}], assumptions=["A request may select one source version for prototype analysis."], limitations=["The current eight-quarter panel and conflicting source snapshots are unsuitable for validated production forecasting.", "No point forecast is returned."], source_file=source, context_files=list(dict.fromkeys(["validate.md", "DATA_DICTIONARY.md"] + payload.get("files", []))))
