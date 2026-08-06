# CSV validation report

Generated after inventorying every original CSV in the project and semantically validating the compatible yield files, market snapshots, compact summary, and documented metadata claims.

## Scope and consolidation policy

- Original source CSV files reviewed: **18** (generated `consolidated_yield_data.csv` is excluded from the source inventory).
- Strictly compatible data files: `yield_data.csv` and `yield_data1.csv`.
- Consolidated output: `consolidated_yield_data.csv` with **118 data rows** and **61 columns** (59 shared fields plus `source_file` and `source_row`).
- Every original CSV was preserved; no source file was edited, overwritten, renamed, or deleted.
- The two yield sources were appended as separate versions because all 59 matching symbol records differ. Provenance is retained so a canonical version can be chosen later.

## Inventory

| File | Data rows | Columns | Bytes | SHA-256 prefix |
|---|---:|---:|---:|---|
| `table-1786042509301.csv` | 4 | 2 | 473 | `89e68300f0824f62` |
| `table-1786042973389.csv` | 7 | 3 | 965 | `8c53403cf6c7e297` |
| `table-1786043097206.csv` | 7 | 3 | 965 | `8c53403cf6c7e297` |
| `table-1786043374524.csv` | 1 | 90 | 2852 | `c18c506ca600d93c` |
| `table-1786043383034.csv` | 1 | 90 | 2805 | `7db5e1b92445ab00` |
| `table-1786043389453.csv` | 1 | 87 | 2744 | `718d4514c7f0341c` |
| `table-1786043396050.csv` | 1 | 87 | 2777 | `297532552bf341f6` |
| `table-1786043404706.csv` | 1 | 87 | 2739 | `8595ad05f020f7a0` |
| `table-1786043409882.csv` | 1 | 87 | 2772 | `3e6b3fd19cbddf47` |
| `table-1786043414639.csv` | 1 | 87 | 2740 | `bcee03a262e295f5` |
| `table-1786043423210.csv` | 1 | 87 | 2696 | `36142b8116057f95` |
| `table-1786043428259.csv` | 1 | 87 | 2791 | `31938ea4d6f3aae0` |
| `table-1786044177764.csv` | 4 | 3 | 727 | `24027ac922bfd49a` |
| `table-1786044184987.csv` | 7 | 3 | 694 | `5aa86737c483c739` |
| `table-1786044192628.csv` | 5 | 7 | 285 | `528c9084854c48fe` |
| `table-1786044273973.csv` | 5 | 3 | 371 | `7f8c4697c5ce0b08` |
| `yield_data.csv` | 59 | 59 | 24354 | `fadfef2157073286` |
| `yield_data1.csv` | 59 | 59 | 25071 | `113b91d1cb750f42` |

## Compatibility groups

### Consolidated

- `yield_data.csv` and `yield_data1.csv` have identical 59-column headers and 59 rows each.
- They are not value-identical: **59/59 rows** differ across **3050 cells** and **53 columns**.

### Not consolidated

- The nine 87/90-column `table-*.csv` market snapshots are one-row exports with heterogeneous headers and column order.
- The small tables were classified by their headers and contents as metadata, feature descriptions, source notes, or a compact summary; their schemas are not compatible with the yield datasets.

## Exact issues and warnings

### Stale metadata

- **`table-1786042509301.csv:5:Purpose`** — `yield_data.csv: 59 rows × 17 columns`; actual dimensions are 59 data rows × 59 columns.
- **`table-1786044273973.csv:2:Size`** — `index.html: claimed 2967 B`; actual 3925 B.
- **`table-1786044273973.csv:2:Size`** — `styles.css: claimed 6693 B`; actual 10718 B.
- **`table-1786044273973.csv:2:Size`** — `matrix.js: claimed 9731 B`; actual 15120 B.

### Duplicate files

- **`table-1786042973389.csv` and `table-1786043097206.csv`** are byte-identical (SHA-256 prefix `8c53403cf6c7e297`). This is redundant, not a row-value error.

### Compact summary conflicts

- **`table-1786044192628.csv:6:Yield`** — `15.72%`; vs yield_data.csv:10:agg_current=15.63.
- **`table-1786044192628.csv:6:Volatility`** — `78.0%`; vs yield_data.csv:10:volatility_annualized_current=66.84.
- **`table-1786044192628.csv:6:Sharpe`** — `17.590`; vs yield_data.csv:10:sharpe_ratio_current=20.392.

### Snapshot precision/value discrepancies

- **`table-1786043396050.csv:2:regularMarketPrice`** — `0.20435`; vs yield_data.csv:6:price_end_current_usd=0.204. These may be rounding or snapshot-time differences and were not silently corrected.
- **`table-1786043404706.csv:2:regularMarketPrice`** — `1.0339`; vs yield_data.csv:7:price_end_current_usd=1.03. These may be rounding or snapshot-time differences and were not silently corrected.
- **`table-1786043409882.csv:2:regularMarketPrice`** — `6.452`; vs yield_data.csv:8:price_end_current_usd=6.45. These may be rounding or snapshot-time differences and were not silently corrected.
- **`table-1786043414639.csv:2:regularMarketPrice`** — `0.8223`; vs yield_data.csv:9:price_end_current_usd=0.82. These may be rounding or snapshot-time differences and were not silently corrected.
- **`table-1786043423210.csv:2:regularMarketPrice`** — `1.363`; vs yield_data.csv:10:price_end_current_usd=1.36. These may be rounding or snapshot-time differences and were not silently corrected.

### Yield-source version conflicts

- **`yield_data.csv:2–60` versus `yield_data1.csv:2–60`** — every matching symbol row differs (59/59 rows; 3050 changed cells).
- Changed columns and exact row ranges:
  - `active_addresses` at rows `2–60` in both files.
  - `agg_current` at rows `2–60` in both files.
  - `agg_prior` at rows `2–60` in both files.
  - `avg_24h_volume_m_usd_current` at rows `2–60` in both files.
  - `avg_24h_volume_m_usd_prior` at rows `2–60` in both files.
  - `beta_vs_btc` at rows `2–60` in both files.
  - `beta_vs_eth` at rows `2–60` in both files.
  - `change_pp` at rows `2–56, 58–60` in both files.
  - `circulating_supply` at rows `2–60` in both files.
  - `correlation_btc` at rows `2–60` in both files.
  - `correlation_eth` at rows `2–60` in both files.
  - `daily_tx_count` at rows `2–60` in both files.
  - `fdv_to_mcap_ratio` at rows `2–60` in both files.
  - `inflation_rate_pct` at rows `2–60` in both files.
  - `investment_score` at rows `2–60` in both files.
  - `ma50_200_cross_pct` at rows `2–60` in both files.
  - `max_drawdown_current_pct` at rows `2–60` in both files.
  - `max_drawdown_prior_pct` at rows `2–60` in both files.
  - `mcap_change_pct` at rows `2–60` in both files.
  - `mcap_end_current_usd` at rows `2–60` in both files.
  - `mcap_end_prior_usd` at rows `2–60` in both files.
  - `mcap_start_current_usd` at rows `2–60` in both files.
  - `mcap_start_prior_usd` at rows `2–60` in both files.
  - `momentum_90d_pct` at rows `2–60` in both files.
  - `notes` at rows `2–6, 9–10, 25` in both files.
  - `outperformance_vs_market_pp` at rows `2–30, 32–60` in both files.
  - `price_change_pct_current` at rows `2–60` in both files.
  - `price_change_pct_prior` at rows `2–60` in both files.
  - `price_end_current_usd` at rows `2–60` in both files.
  - `price_end_prior_usd` at rows `2–60` in both files.
  - `price_start_current_usd` at rows `2–60` in both files.
  - `price_start_prior_usd` at rows `2–60` in both files.
  - `q1_25_prior` at rows `2–43, 45–60` in both files.
  - `q1_26_current` at rows `2–60` in both files.
  - `q2_25_prior` at rows `2–60` in both files.
  - `q2_26_current` at rows `2–6, 8–60` in both files.
  - `q3_24_prior` at rows `2–27, 29–60` in both files.
  - `q3_25_current` at rows `2–60` in both files.
  - `q3_26_forward_yield` at rows `2–60` in both files.
  - `q4_24_prior` at rows `2–52, 54–60` in both files.
  - `q4_25_current` at rows `2–60` in both files.
  - `risk_adjusted_yield` at rows `2–60` in both files.
  - `rsi_14d` at rows `2–60` in both files.
  - `sharpe_ratio_current` at rows `2–60` in both files.
  - `sharpe_ratio_prior` at rows `2–60` in both files.
  - `tvl_usd` at rows `2–60` in both files.
  - `volatility_annualized_current` at rows `2–60` in both files.
  - `volatility_annualized_prior` at rows `2–60` in both files.
  - `volume_trend_pct` at rows `2–60` in both files.
  - `yield_direction_next_q` at rows `2–3, 5–6, 8–11, 14–17, 19, 22–23, 25–26, 28, 30–31, 33–36, 38, 41–45, 48, 50–52, 55–59` in both files.
  - `yield_trend_slope` at rows `2–60` in both files.
  - `yield_volatility` at rows `2–60` in both files.
  - `yield_vs_category_avg` at rows `2–60` in both files.

## Validation results

- Row-width consistency: **pass**.
- Duplicate symbols in yield files: **none**.
- Empty cells in yield files: **none**.
- Formula checks: **pass**.
- Documented range checks: **pass**.

## Interpretation notes

- The yield files are alternative generated snapshots rather than complementary tables. Their conflicts should be resolved before treating the consolidated file as a single canonical dataset.
- The market snapshots cannot be safely unioned with the yield schema without an explicit field mapping and timestamp policy.
- Small price differences found in snapshot comparisons are consistent with rounded values in the yield file; they are documented rather than changed.
- The ATOM summary row contains substantive yield, volatility, and Sharpe conflicts and should be reconciled before use as a view of `yield_data.csv`.
- **Corrected forecasting caveat:** The current dataset’s limited history and conflicting source versions make it unsuitable for validated production forecasting. Production forecasting requires source reconciliation, additional dated observations, leakage-controlled walk-forward testing, baseline comparison, and independently observed future outcomes.

## Blocks.ai-compatible expert-agent scaffold

Eleven local expert-agent cards were created in `blocks_agents/`. They are file-backed orchestration manifests, not published network agents. The cards use a researched Blocks agent-card shape: `identity`, `capabilities.taskKinds`, `tags`, `runtime.handler`, `io.inputs`, and `io.outputs`. `blocks_agents/agent_cards.json` indexes all eleven cards.

### Eleven expert agents

1. `data_provenance_auditor` — schema, hashes, source conflicts, and `source_file`/`source_row` lineage.
2. `yield_methodology_expert` — staking, lending-equivalent, inflation, annualization, aggregates, and methodology notes.
3. `crypto_risk_analyst` — volatility, drawdown, beta, correlation, Sharpe, and risk-adjusted yield context.
4. `defi_liquidity_analyst` — volume, TVL, active addresses, transaction activity, and liquidity-risk proxies.
5. `tokenomics_sustainability_expert` — nominal yield versus inflation, FDV/mcap, supply, and market-cap dynamics.
6. `quant_forecasting_expert` — forecast readiness, targets, chronological splits, baselines, and uncertainty.
7. `portfolio_scenario_expert` — transparent, educational yield/risk/liquidity constraint scenarios.
8. `model_validation_guardian` — source duplication, circular targets, leakage, calibration, and backtesting gates.
9. `matrix_research_insights_agent` — user-facing insights aligned with the existing matrix, timeline, legends, and tooltips.
10. `crypto_research_communications_agent` — evidence-linked, cautious, non-advisory research notes.
11. `feature_engineering_expert` — recomputed yield momentum, mcap/TVL, risk, and category-premium features.

### Blocks compatibility and safe boundary

- Shared read-only context is declared in `blocks_agents/README.md` and the card manifests, including `validate.md`, `DATA_DICTIONARY.md`, both yield sources, the provenance-preserving consolidation, and the current UI files.
- Requests use JSON input with a declared `request` part; outputs are structured JSON or Markdown artifacts with status, evidence locations, assumptions, and limitations.
- The cards are local scaffolding with runnable standard-library handlers. `blocks_agents/loader.py` resolves the manifest-relative `./handlers/...` paths, while `handlers/common.py` enforces the declared read-only context allowlist and common artifact envelope. No Blocks account, API key, SDK installation, registration, or publication was performed. A Blocks CLI/configuration check should be run only after the official SDK/CLI is explicitly installed and credentials are supplied by the user.
- Agents must never treat both conflicting yield files as independent training observations, must label estimated/derived/target fields, and must not present outputs as guaranteed returns or financial advice.

## Research-backed user value and real problem opportunities

The dataset can support useful research and decision-support products, but it is not yet suitable for unattended trading or investment recommendations. The main reason is provenance: the two yield files contain alternative values for every asset row, and `table-1786044184987.csv:2–8` explicitly distinguishes real, estimated, and computed fields. Product screens should expose that distinction instead of presenting every number as equally observed.

### Highest-value use cases

| Priority | User problem | Product outcome | Useful fields | Why it creates value |
|---|---|---|---|---|
| 1 | “Which yield is actually comparable?” Headline APY mixes staking, lending equivalents, inflation rewards, and other mechanisms. | A yield-comparison screener showing annualized yield, methodology, asterisk/annualization status, prior-vs-current change, and a comparable-yield band. | `agg_current`, `agg_prior`, `change_pp`, `is_annualized`, `notes`, `category`, quarter columns | Makes the existing matrix actionable while warning users when two yields are not economically identical. |
| 2 | “Is the yield worth the risk?” A high yield can coexist with high volatility, drawdown, beta, or weak risk-adjusted performance. | A risk-adjusted opportunity card with yield, volatility, current/prior drawdown, Sharpe, beta, and a confidence/data-quality badge. | `agg_current`, `volatility_annualized_current`, `max_drawdown_current_pct`, `sharpe_ratio_current`, `beta_vs_btc`, `beta_vs_eth`, `risk_adjusted_yield` | Helps users compare reward and downside together instead of sorting by APY alone. Treat `risk_adjusted_yield` as a supplied/computed feature, not an independent model target. |
| 3 | “Can I exit or deploy capital safely?” Yield is less useful if liquidity is deteriorating. | A liquidity watchlist ranking assets by volume trend, market cap, TVL, active addresses, and transactions, with “thin liquidity” warnings. | `avg_24h_volume_m_usd_current`, `avg_24h_volume_m_usd_prior`, `volume_trend_pct`, `mcap_end_current_usd`, `tvl_usd`, `active_addresses`, `daily_tx_count` | Surfaces exit/liquidity risk before a user chases a high quoted yield. This is a screening proxy, not a slippage guarantee. |
| 4 | “Is the yield sustainable or mostly dilution?” Token rewards can be offset by inflation and dilution. | A sustainability view showing yield beside inflation, FDV/market-cap ratio, circulating supply, and market-cap change. | `agg_current`, `inflation_rate_pct`, `fdv_to_mcap_ratio`, `circulating_supply`, `mcap_change_pct`, `notes` | Separates nominal reward from tokenomics pressure. A true net-yield calculation still needs fees, token price path, lockups, and reward composition. |
| 5 | “Which data should I trust?” Conflicting snapshots and rounded values can produce bad decisions or misleading research. | A provenance and data-quality panel showing source version, source row, freshness, precision, validation status, and conflicts. | `source_file`, `source_row` in `consolidated_yield_data.csv`; `validate.md`; original snapshot files | Prevents users from unknowingly mixing incompatible versions. This is an immediate operational problem already demonstrated by the audit. |
| 6 | “How does an asset compare with similar assets?” Raw cross-category ranking can be misleading. | Category-relative benchmarking with yield premium, trend, volatility, liquidity, and drawdown compared within `category`. | `category`, `yield_vs_category_avg`, `yield_trend_slope`, `yield_volatility`, `max_drawdown_current_pct` | Gives researchers a fairer peer comparison than one global leaderboard. |
| 7 | “How should a portfolio balance yield and concentration?” | A scenario tool that applies user constraints—maximum drawdown, category caps, liquidity minimums, and target yield—and explains trade-offs. | `agg_current`, `max_drawdown_current_pct`, `category`, `correlation_btc`, `correlation_eth`, `beta_vs_btc`, `beta_vs_eth`, volume fields | Turns the dataset into transparent what-if analysis rather than a one-number recommendation. It must be labeled educational/decision support. |
| 8 | “Can I monitor protocol/asset changes over time?” | A quarterly research dashboard for yield trend, market-cap change, volume trend, TVL, and address/transaction activity. | Eight quarterly yield fields, `yield_trend_slope`, `mcap_change_pct`, `volume_trend_pct`, `tvl_usd`, `active_addresses`, `daily_tx_count` | Helps analysts find regime changes and investigate why yield moved. |

### Recommended product sequence

1. **MVP screener:** comparable-yield card plus methodology/provenance badges, current/prior change, volatility, drawdown, and liquidity trend.
2. **Data-quality layer:** force a canonical source selection between `yield_data.csv` and `yield_data1.csv`; retain the other as an alternate snapshot and show conflicts.
3. **Alerts:** notify on yield deterioration, volume contraction, drawdown worsening, or a large gap between nominal yield and category-relative/risk-adjusted yield.
4. **Scenario analysis:** let users set risk, liquidity, and category constraints; show the selected assumptions and sensitivity.
5. **Forecasting:** only after adding dated historical observations and resolving source/version identity.

## Prediction and modeling ideas

These are candidate research tasks, not validated investment signals. The current dataset has only eight quarter columns per asset and 59 asset rows per source. That is insufficient for reliable asset-level forecasting without additional dated history. The `q3_26_forward_yield`, `yield_direction_next_q`, `risk_adjusted_yield`, `outperformance_vs_market_pp`, and `investment_score` fields are already supplied targets or derived outputs; they are not validated ground truth and must not be treated as ordinary observed outcomes until their generation process and time alignment are documented.

### Column provenance and modeling status

The repository does not provide a complete column-level provenance registry. Until one is added, use this conservative working classification based on `table-1786044184987.csv:2–8`, `DATA_DICTIONARY.md`, and the audit findings:

| Status | Current fields | Safe interpretation |
|---|---|---|
| Source-like / reported inputs | `symbol`, `name`, `category`, `color`, `icon`, `notes`, supplied market-cap/price/volume/supply/TVL/address/transaction fields, and quarterly yield fields | Use only with `source_file`, source date, measurement window, and freshness metadata. Several are reported as synthetic estimates or mixed-source values; do not assume all are independently observed. |
| Estimated or synthetic features | The fields identified as estimated in `table-1786044184987.csv:2–8`, especially many volatility, drawdown, beta, correlation, RSI, momentum, and technical fields | Appropriate for prototype screens and sensitivity analysis, not for claims of live predictive accuracy. |
| Derived features | `agg_prior`, `agg_current`, `change_pp`, `yield_volatility`, `yield_trend_slope`, `yield_vs_category_avg`, `risk_adjusted_yield` | Recompute and document formulas where possible. `risk_adjusted_yield` is derived from yield and volatility and is not an independent signal. |
| Supplied model labels / targets | `q3_26_forward_yield`, `yield_direction_next_q`, `outperformance_vs_market_pp`, `investment_score` | Treat as labels produced by the source pipeline, not validated future observations. Do not use a label as a feature or claim forecast accuracy from it without an independently observed outcome. |
| Conflicting / unresolved | Any row where `yield_data.csv` and `yield_data1.csv` disagree; the compact ATOM summary and snapshot precision conflicts documented above | Require reconciliation or display a conflict badge; do not silently average or select a winner. |

A future canonical dataset should add `observation_status` (`observed`, `estimated`, `derived`, `target`, or `conflicting`), `source_name`, `source_url`, `as_of_date`, `measurement_window`, and `refresh_timestamp` per record or field group.

### 1. Next-quarter yield forecast — regression

- **User question:** “What yield range might I see next quarter?”
- **Candidate target:** a future observed quarterly yield, or the supplied `q3_26_forward_yield` only as a clearly labeled model target.
- **Candidate features:** lagged quarterly yields, `agg_prior`, `yield_trend_slope`, `yield_volatility`, `volatility_annualized_prior`, prior-window volume trend, prior-window momentum, `inflation_rate_pct`, and `category`.
- **Timestamp rule:** if the forecast is made before the current window ends, do not use `agg_current`, `volatility_annualized_current`, `mcap_end_current_usd`, current-window price/volume fields, or any other current/future value. Those features become valid only for a forecast made after that measurement window.
- **Output:** point forecast plus prediction interval and “low/medium/high confidence,” not a single guaranteed APY.
- **Metrics:** MAE, RMSE, and MASE against a last-value and rolling-mean baseline. Report errors by category and by source version.
- **Leakage rule:** do not use `q3_26_forward_yield`, `agg_current`, `volatility_annualized_current`, or other current/future fields when simulating a forecast made before that period.

### 2. Yield direction alert — classification

- **User question:** “Is this asset’s yield more likely to rise or fall next quarter?”
- **Candidate target:** `yield_direction_next_q`, after confirming its label definition and time alignment.
- **Candidate features:** only information available before the target period: lagged yield changes, prior-window volatility/drawdown, `yield_trend_slope`, prior-window volume trend, prior-window momentum, prior-window RSI/technical values, category, and prior liquidity fields. Verify that the supplied label is actually aligned to the next quarter before training.
- **Timestamp rule:** do not use current-window fields when simulating a decision made before the current window; otherwise the classifier has look-ahead leakage.
- **Output:** calibrated probability of increase, neutral/uncertain band, and reason codes such as “negative yield trend” or “volume weakening.”
- **Metrics:** balanced accuracy, ROC-AUC, precision/recall, Brier score, and calibration curve. A 70% prediction should occur approximately 70% of the time in its validation bucket.

### 3. Yield deterioration / stress alert — event detection

- **User question:** “Which assets are becoming less attractive before the headline APY collapses?”
- **Candidate target:** define from future observations, for example a future yield drop of at least 1 percentage point, a future drawdown threshold, or a simultaneous yield decline and volume contraction.
- **Features:** yield slope/volatility, prior drawdown, beta, volume trend, TVL, active addresses, inflation, and category.
- **Output:** ranked alert queue with the trigger variables and an audit link to the supporting rows.
- **Metrics:** precision at top-k, recall, false alerts per quarter, and average lead time. This is more operationally useful than an opaque “buy score.”

### 4. Liquidity-stress forecast — regression/classification

- **User question:** “Could exiting this position become harder next period?”
- **Candidate target:** next-period volume contraction, TVL contraction, or a defined liquidity-risk event. Do not use current `volume_trend_pct` as both feature and target.
- **Features:** prior average volume, market cap, TVL, active addresses, transactions, volatility, beta, and category.
- **Output:** probability of liquidity deterioration plus a watchlist explanation.
- **Metrics:** PR-AUC for rare events, recall at a chosen alert budget, and calibration—not accuracy alone.

### 5. Category-relative ranking — ranking/recommendation research

- **User question:** “Which assets offer the best current yield after accounting for risk and peer context?”
- **Candidate score:** an explicitly documented utility score built from current yield, drawdown penalty, volatility penalty, liquidity floor, inflation penalty, and category-relative yield.
- **Important restriction:** do not train on or reuse `investment_score` as an objective while also using its component fields; that is circular target leakage. Recompute a transparent score from user-selected weights and show the formula.
- **Metrics:** rank correlation, top-k stability across time, turnover, worst-case drawdown in a historical walk-forward simulation, and sensitivity to weights.

### 6. Anomaly and provenance detection — unsupervised/data operations

- **User question:** “Which records require human review before publication?”
- **Signals:** disagreement between the two yield versions, compact-table conflicts, snapshot precision gaps, unusual yield jumps, impossible ranges, missing fields, and stale timestamps.
- **Output:** data-quality queue with severity, exact file/row/column location, and suggested action (reconcile, label as estimated, or exclude).
- **Metrics:** confirmed issue precision, review time saved, false-positive rate, and percentage of published records with traceable provenance.

## Modeling guardrails

- **Resolve source identity first.** Never train on both versions of the same asset/time window as if they were independent observations. `consolidated_yield_data.csv` is a provenance-preserving comparison file, not automatically a training table. Train separately by `source_file`, or select and document one canonical source before modeling.
- **Separate observed, estimated, and derived data.** `table-1786044184987.csv:2–8` says that many fields are synthetic estimates or computed targets. Add an `observation_status` field in a future canonical dataset.
- **Use chronological validation.** Use expanding-window or walk-forward splits, not random train/test splits. Scikit-learn documents this pattern in [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).
- **Calibrate probabilities.** For direction/stress alerts, use a held-out calibration procedure and report Brier score and reliability plots. See [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html).
- **Start with baselines.** Compare every model to persistence/last-value, rolling mean, category mean, and “no alert” baselines. A more complex model is not useful unless it improves out-of-sample performance and remains stable by category and time.
- **Quantify uncertainty.** Use prediction intervals, confidence bands, or conformal intervals; do not show a point forecast as a promise.
- **Avoid false precision.** The rounded snapshot mismatches already documented in this report show why outputs should preserve source precision and display freshness/rounding metadata.
- **Use conservative language.** Present results as research, monitoring, and scenario analysis—not guaranteed return, safety, or financial advice. The [SEC Investor.gov crypto asset resources](https://www.investor.gov/additional-resources/spotlight/crypto-assets) are a useful reference for risk-disclosure design.
- **Define TVL consistently.** If adding live DeFi data, document methodology and protocol coverage; [DefiLlama’s methodology documentation](https://docs.llama.fi/) is a useful reference point.
- **Explain staking mechanics.** Yield methodology should distinguish native staking, pooled/liquid staking, lending, MEV, inflation rewards, and fees. [Ethereum’s staking overview](https://ethereum.org/staking/) illustrates why these mechanisms should not be treated as interchangeable.

## Practical feature backlog

- Add `observation_status`: observed, estimated, derived, target, or conflicting, with a field-level provenance map for the current synthetic/estimated claims.
- Compute transparent derived features through `feature_engineering_expert`: `yield_momentum = yield_trend_slope * yield_volatility`; `mcap_to_tvl = mcap_end_current_usd / tvl_usd`; `risk_score = beta_vs_btc * volatility_annualized_current / sharpe_ratio_current`; `yield_premium = agg_current - yield_vs_category_avg`. Preserve `null` and a warning for zero denominators.
- Add `as_of_date`, `measurement_window`, `source_name`, `source_url`, and `refresh_timestamp` to each record.
- Add a canonical resolved dataset rather than using the two-source append-only consolidation for modeling.
- Add explicit `net_yield_after_inflation` only after defining the token-price, reward, fee, and inflation assumptions.
- Add historical observations beyond one row per asset and eight quarterly snapshots so forecasts can be evaluated genuinely out of sample.
- Add alert thresholds and user preferences instead of hard-coding a universal risk tolerance.
- Add an audit link from every UI metric to its source file, row, column, and validation status.

## References

- SEC Investor.gov — [Crypto Assets](https://www.investor.gov/additional-resources/spotlight/crypto-assets)
- DefiLlama — [Methodology documentation](https://docs.llama.fi/)
- Ethereum.org — [Staking](https://ethereum.org/staking/)
- scikit-learn — [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
- scikit-learn — [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
