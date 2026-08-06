from .common import derived_features, evidence, load_source, report, select, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Reviewing volume, TVL, and activity proxies")
    findings = []
    for row in rows:
        volume = value(row, "avg_24h_volume_m_usd_current")
        tvl = value(row, "tvl_usd")
        findings.append({"symbol": row["symbol"], "volume_current_m_usd": volume, "volume_trend_pct": value(row, "volume_trend_pct"), "tvl_usd": tvl, "active_addresses": value(row, "active_addresses"), "daily_transactions": value(row, "daily_tx_count"), "market_cap_usd": value(row, "mcap_end_current_usd"), "volume_to_tvl": volume * 1_000_000 / tvl if tvl else None, "mcap_to_tvl": derived_features(row)["mcap_to_tvl"], "evidence": evidence(row, filename)})
    return report("defi_liquidity_analyst", "PASS" if findings else "WARNING", "Liquidity and adoption proxies are reported with explicit limits; they are not a slippage guarantee.", findings, limitations=["Snapshots are not real-time.", "Volume, addresses, and transactions can include bots, routing activity, or sybil noise.", "Granular pool depth and slippage are not present."], source_file=filename, context_files=payload.get("files", []))
