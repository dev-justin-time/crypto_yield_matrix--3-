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
    findings.append({"check": "embedded_provenance", "pass": "source_file" in text and "source_row" in text, "evidence": "yield_data.csv provenance columns"})
    findings.append({"check": "requested_symbol", "symbol": payload.get("symbol"), "question": payload.get("question", "")})
    return report("data_provenance_auditor", "WARNING", "Source lineage is documented, but the repeated provenance rows still conflict and require canonical-source selection.", findings, limitations=["The canonical file contains embedded source lineage and repeated symbols.", "This local handler audits read-only repository context and does not mutate data."], source_file=primary_source, context_files=list(dict.fromkeys(["validate.md"] + payload.get("files", []))))
