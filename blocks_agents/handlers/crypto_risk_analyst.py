from .common import evidence, load_source, report, select, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Computing yield and downside context")
    findings = []
    for row in rows:
        findings.append({"symbol": row["symbol"], "yield_pct": value(row, "agg_current"), "volatility_pct": value(row, "volatility_annualized_current"), "drawdown_pct": value(row, "max_drawdown_current_pct"), "sharpe": value(row, "sharpe_ratio_current"), "beta_btc": value(row, "beta_vs_btc"), "beta_eth": value(row, "beta_vs_eth"), "risk_adjusted_yield": value(row, "risk_adjusted_yield"), "evidence": evidence(row, filename)})
    return report("crypto_risk_analyst", "PASS" if findings else "WARNING", "Risk context is shown beside yield; outputs are screening evidence, not safety or return guarantees.", findings, limitations=["Risk metrics may be estimated or derived according to table-1786044184987.csv.", "No live price or liquidity feed is used."], source_file=filename, context_files=payload.get("files", []))
