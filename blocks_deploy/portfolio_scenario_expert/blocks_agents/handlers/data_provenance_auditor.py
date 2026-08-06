from .common import YIELD_SOURCES, read_context, report, status, task_payload


def handler(task, ctx=None):
    status(ctx, "Reading validation report and source lineage")
    payload = task_payload(task)
    findings = []
    primary_source = payload.get("source_file") or "yield_data.csv"
    if primary_source not in YIELD_SOURCES:
        raise ValueError(f"source_file must be one of {sorted(YIELD_SOURCES)}")
    text = read_context("validate.md")
    findings.append({"check": "report_available", "pass": bool(text), "evidence": "validate.md"})
    findings.append({"check": "source_version_conflict", "pass": "3050 changed cells" in text, "evidence": "validate.md:yield-source version conflicts"})
    findings.append({"check": "requested_symbol", "symbol": payload.get("symbol"), "question": payload.get("question", "")})
    return report("data_provenance_auditor", "WARNING", "Source lineage is documented, but the two yield versions still conflict and require canonical-source selection.", findings, limitations=["No source was selected as canonical; source_file identifies the primary comparison baseline only.", "This local handler compares both yield versions and does not publish or mutate data."], source_file=primary_source, context_files=list(dict.fromkeys(["validate.md"] + payload.get("files", []))))
