from .common import display_number, evidence, load_source, report, select, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Preparing a traceable non-advisory research note")
    findings = []
    for row in rows:
        findings.append({"symbol": row["symbol"], "headline": f"{row['name']} current aggregate yield: {display_number(value(row, 'agg_current'), '%')}", "evidence": {**evidence(row, filename, int(row["source_row"]) if row.get("source_row") not in (None, "") else None), "fields": ["agg_current", "change_pp", "notes", "is_annualized"]}, "status": "canonical-dataset row"})
    return report("crypto_research_communications_agent", "WARNING" if findings else "FAIL", "This note is research communication only; it does not provide investment advice, a safety claim, or a guaranteed return.", findings, assumptions=["The canonical yield_data.csv dataset is used."], limitations=["The project contains embedded provenance rows and estimated/derived/target fields.", "Exact row references should be attached by a production adapter."], source_file=filename, context_files=payload.get("files", []))
