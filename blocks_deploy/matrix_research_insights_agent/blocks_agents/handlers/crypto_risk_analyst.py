from .common import asset_enrichment, derived_features, evidence, load_source, report, select, snapshot_research, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Computing yield and downside context")
    findings = []
    for row in rows:
        features = derived_features(row)
        findings.append({"symbol": row["symbol"], "yield_pct": value(row, "agg_current"), "volatility_pct": value(row, "volatility_annualized_current"), "drawdown_pct": value(row, "max_drawdown_current_pct"), "sharpe": value(row, "sharpe_ratio_current"), "beta_btc": value(row, "beta_vs_btc"), "beta_eth": value(row, "beta_vs_eth"), "risk_adjusted_yield": value(row, "risk_adjusted_yield"), "risk_score": features["risk_score"], "yield_momentum": features["yield_momentum"], "asset_enrichment": asset_enrichment(row["symbol"]), "market_snapshot_research": snapshot_research(row["symbol"]), "evidence": evidence(row, filename)})
    return report("crypto_risk_analyst", "PASS" if findings else "WARNING", "Risk context is shown beside yield; outputs are screening evidence, not safety or return guarantees.", findings, limitations=["Named market snapshots are supplied evidence and may be stale; they are not a live price feed.", "Live market context is optional, separately labeled, and may be stale or unavailable; it never replaces canonical yield evidence."], source_file=filename, context_files=payload.get("files", []))
