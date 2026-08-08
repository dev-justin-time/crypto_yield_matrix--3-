from .common import asset_enrichment, derived_features, evidence, load_source, report, select, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Mapping matrix metrics to a traceable research response")
    findings = []
    for row in rows:
        features = derived_features(row)
        findings.append({"symbol": row["symbol"], "name": row["name"], "category": row.get("category"), "prior_aggregate_pct": value(row, "agg_prior"), "current_aggregate_pct": value(row, "agg_current"), "change_pp": value(row, "change_pp"), "forecast_label_pct": value(row, "q3_26_forward_yield"), "annualized": row.get("is_annualized") == "1", "methodology": row.get("notes", ""), **features, "asset_enrichment": asset_enrichment(row["symbol"]), "evidence": evidence(row, filename)})
    return report("matrix_research_insights_agent", "WARNING" if findings else "FAIL", "Dashboard-aligned matrix findings include quarter aggregates, changes, methodology, and target-status caveats.", findings, limitations=["Forecast labels are supplied targets, not independently validated forecasts.", "The current UI loads canonical yield_data.csv plus generated enrichment and an optional separately labeled live overlay."], source_file=filename, context_files=payload.get("files", []))
