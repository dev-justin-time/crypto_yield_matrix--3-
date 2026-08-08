from .common import asset_enrichment, derived_features, evidence, load_source, report, select, status, task_payload, value


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Reviewing volume, TVL, and activity proxies")
    findings = []
    for row in rows:
        volume = value(row, "avg_24h_volume_m_usd_current")
        tvl = value(row, "tvl_usd")
        features = derived_features(row)
        findings.append({"symbol": row["symbol"], "volume_current_m_usd": volume, "volume_trend_pct": value(row, "volume_trend_pct"), "tvl_usd": tvl, "active_addresses": value(row, "active_addresses"), "daily_transactions": value(row, "daily_tx_count"), "market_cap_usd": value(row, "mcap_end_current_usd"), "volume_to_tvl": volume * 1_000_000 / tvl if volume is not None and tvl not in (None, 0) else None, "mcap_to_tvl": features["mcap_to_tvl"], "asset_enrichment": asset_enrichment(row["symbol"]), "evidence": evidence(row, filename)})
    return report("defi_liquidity_analyst", "PASS" if findings else "WARNING", "Liquidity and adoption proxies are reported with explicit limits; they are not a slippage guarantee.", findings, limitations=["Historical snapshots are not real-time; the optional live overlay carries its own provider timestamp and freshness status.", "Volume, addresses, and transactions can include bots, routing activity, or sybil noise.", "Granular pool depth and slippage are not present."], source_file=filename, context_files=payload.get("files", []))
