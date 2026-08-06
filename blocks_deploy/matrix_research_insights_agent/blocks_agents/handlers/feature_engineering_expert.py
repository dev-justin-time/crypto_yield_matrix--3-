from .common import derived_features, evidence, load_source, numeric_value, report, select, status, task_payload


def handler(task, ctx=None):
    payload = task_payload(task)
    filename = payload.get("source_file", "yield_data.csv")
    rows = select(load_source(filename), payload)
    status(ctx, "Computing transparent research features from source fields")
    findings = []
    for row in rows:
        features = derived_features(row)
        warnings = []
        if numeric_value(row, "tvl_usd") is None:
            warnings.append("mcap_to_tvl unavailable because tvl_usd is missing, invalid, or zero")
        if numeric_value(row, "sharpe_ratio_current") is None:
            warnings.append("risk_score unavailable because sharpe_ratio_current is missing, invalid, or zero")
        for field in ["yield_trend_slope", "yield_volatility", "mcap_end_current_usd", "beta_vs_btc", "volatility_annualized_current", "agg_current", "yield_vs_category_avg"]:
            if numeric_value(row, field) is None:
                warnings.append(f"derived feature input unavailable: {field}")
        findings.append({
            "symbol": row["symbol"],
            **features,
            "formula_inputs": {
                "yield_trend_slope": numeric_value(row, "yield_trend_slope"),
                "yield_volatility": numeric_value(row, "yield_volatility"),
                "mcap_end_current_usd": numeric_value(row, "mcap_end_current_usd"),
                "tvl_usd": numeric_value(row, "tvl_usd"),
                "beta_vs_btc": numeric_value(row, "beta_vs_btc"),
                "volatility_annualized_current": numeric_value(row, "volatility_annualized_current"),
                "sharpe_ratio_current": numeric_value(row, "sharpe_ratio_current"),
                "agg_current": numeric_value(row, "agg_current"),
                "yield_vs_category_avg": numeric_value(row, "yield_vs_category_avg"),
            },
            "warnings": warnings,
            "evidence": evidence(row, filename),
        })
    return report(
        "feature_engineering_expert",
        "PASS" if findings else "WARNING",
        "Derived yield, market-cap, liquidity, risk, and peer-premium features were recomputed from source fields.",
        findings,
        assumptions=["All numeric source fields are interpreted in the units documented by DATA_DICTIONARY.md."],
        limitations=[
            "Derived features inherit the source files' estimated, synthetic, and version-conflict limitations.",
            "mcap_to_tvl and risk_score are undefined when their denominators are zero.",
            "These features are research inputs, not validated investment signals or financial advice.",
        ],
        source_file=filename,
        context_files=list(dict.fromkeys(["DATA_DICTIONARY.md"] + payload.get("files", []))),
    )
