from .common import evidence, load_source, report, select, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Applying user-supplied scenario constraints")
    findings = []
    for row in rows:
        findings.append({"symbol": row["symbol"], "category": row.get("category"), "yield_pct": value(row, "agg_current"), "drawdown_pct": value(row, "max_drawdown_current_pct"), "volatility_pct": value(row, "volatility_annualized_current"), "volume_current_m_usd": value(row, "avg_24h_volume_m_usd_current"), "correlation_btc": value(row, "correlation_btc"), "correlation_eth": value(row, "correlation_eth"), "evidence": evidence(row, filename)})
    return report("portfolio_scenario_expert", "PASS" if findings else "WARNING", "Scenario inputs are summarized with constraints and trade-offs; no recommendation or execution is produced.", findings, assumptions=["User constraints are illustrative and must be supplied explicitly."], limitations=["No covariance matrix, fees, taxes, lockups, or live execution costs are modeled.", "This is educational decision support, not financial advice."], source_file=filename, context_files=payload.get("files", []))
