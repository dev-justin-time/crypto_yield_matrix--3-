from .common import evidence, load_source, report, select, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Comparing nominal yield with inflation and dilution pressure")
    findings = []
    for row in rows:
        nominal = value(row, "agg_current")
        inflation = value(row, "inflation_rate_pct")
        findings.append({"symbol": row["symbol"], "nominal_yield_pct": nominal, "inflation_pct": inflation, "nominal_minus_inflation_pp": nominal - inflation, "fdv_to_mcap": value(row, "fdv_to_mcap_ratio"), "circulating_supply": value(row, "circulating_supply"), "market_cap_change_pct": value(row, "mcap_change_pct"), "methodology": row.get("notes", ""), "evidence": evidence(row, filename)})
    return report("tokenomics_sustainability_expert", "PASS" if findings else "WARNING", "Nominal yield is compared with inflation and dilution proxies without claiming a complete net-yield calculation.", findings, limitations=["Fees, lockups, reward composition, taxes, and token price path are not modeled.", "Inflation-adjusted yield is a diagnostic proxy, not realized return."], source_file=filename, context_files=payload.get("files", []))
