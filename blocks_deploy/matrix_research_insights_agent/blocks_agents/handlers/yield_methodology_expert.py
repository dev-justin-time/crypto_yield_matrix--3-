from .common import evidence, load_source, report, select, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Comparing yield methodology and annualization flags")
    findings = []
    for row in rows:
        findings.append({"symbol": row["symbol"], "yield_current_pct": value(row, "agg_current"), "yield_prior_pct": value(row, "agg_prior"), "change_pp": value(row, "change_pp"), "annualized": row.get("is_annualized") == "1", "methodology": row.get("notes", ""), "category": row.get("category"), "evidence": evidence(row, filename)})
    return report("yield_methodology_expert", "PASS" if findings else "WARNING", "Yield comparison includes methodology notes and annualization status; unlike reward mechanisms are not treated as interchangeable.", findings, limitations=["The files do not provide a normalized APR/APY compounding convention for every row.", "The canonical file may contain repeated symbols with distinct provenance rows."], source_file=filename, context_files=payload.get("files", []))
