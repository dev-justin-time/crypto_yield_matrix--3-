# Yield Data Dictionary — cryptocurrentcy Underlying Asset Cash Yield Matrix

## Core Yield Data (17 columns)
| Column | Type | Description |
|--------|------|-------------|
| symbol | string | Ticker symbol (e.g., BTC, ETH) |
| name | string | Asset name in lowercase |
| color | hex | Brand color for visual rendering |
| icon | string | Single-letter icon identifier |
| q3_24_prior — q2_26_current | float | Quarterly annualized yield % |
| agg_prior | float | 12-month mean yield, prior window |
| agg_current | float | 12-month mean yield, current window |
| change_pp | float | Directional change in percentage points |
| is_annualized | int (0/1) | 1 = annualized/lending-market equivalent |
| notes | string | Asset-specific yield methodology notes |

## Market Data (11 columns)
| Column | Type | Description |
|--------|------|-------------|
| category | string | Asset classification: layer1, defi, payments, oracle, ai, depin, storage, infrastructure, rwa, nft, enterprise, media, privacy, other |
| mcap_start_prior_usd | float | Market cap at start of prior window (USD) |
| mcap_end_prior_usd | float | Market cap at end of prior window (USD) |
| mcap_start_current_usd | float | Market cap at start of current window (USD) |
| mcap_end_current_usd | float | Market cap at end of current window (USD) |
| mcap_change_pct | float | Total market cap change % across full period |
| price_start_prior_usd | float | Token price at start of prior window |
| price_end_prior_usd | float | Token price at end of prior window |
| price_start_current_usd | float | Token price at start of current window |
| price_end_current_usd | float | Token price at end of current window |
| price_change_pct_prior | float | Price change % during prior window |
| price_change_pct_current | float | Price change % during current window |

## Liquidity & On-Chain (5 columns)
| Column | Type | Description |
|--------|------|-------------|
| volatility_annualized_prior | float | Annualized price volatility %, prior window |
| volatility_annualized_current | float | Annualized price volatility %, current window |
| avg_24h_volume_m_usd_prior | float | Average daily volume in millions USD, prior |
| avg_24h_volume_m_usd_current | float | Average daily volume in millions USD, current |
| volume_trend_pct | float | Volume change % between windows |
| active_addresses | float | Estimated active on-chain addresses |
| daily_tx_count | float | Estimated daily transaction count |
| tvl_usd | float | Total value locked in USD (DeFi protocols) |

## Supply & Tokenomics (3 columns)
| Column | Type | Description |
|--------|------|-------------|
| circulating_supply | float | Tokens in circulation |
| inflation_rate_pct | float | Annual token inflation / deflation rate % |
| fdv_to_mcap_ratio | float | Fully diluted valuation / market cap |

## Risk Metrics (6 columns)
| Column | Type | Description |
|--------|------|-------------|
| max_drawdown_prior_pct | float | Maximum peak-to-trough drawdown %, prior |
| max_drawdown_current_pct | float | Maximum peak-to-trough drawdown %, current |
| sharpe_ratio_prior | float | Risk-adjusted return (yield / volatility), prior |
| sharpe_ratio_current | float | Risk-adjusted return, current |
| beta_vs_btc | float | Systematic risk relative to Bitcoin |
| beta_vs_eth | float | Systematic risk relative to Ethereum |

## Correlation & Technical (5 columns)
| Column | Type | Description |
|--------|------|-------------|
| correlation_btc | float | Pearson correlation with BTC price |
| correlation_eth | float | Pearson correlation with ETH price |
| rsi_14d | float | 14-day Relative Strength Index (0–100) |
| ma50_200_cross_pct | float | % distance between 50d and 200d MA |
| momentum_90d_pct | float | 90-day price momentum % |

## Yield Analytics (3 columns)
| Column | Type | Description |
|--------|------|-------------|
| yield_volatility | float | Std dev of 8 quarterly yields |
| yield_trend_slope | float | Linear regression slope across 8 quarters |
| yield_vs_category_avg | float | Asset yield minus category mean yield |

## Prediction Targets (5 columns)
| Column | Type | Description |
|--------|------|-------------|
| q3_26_forward_yield | float | **Target**: Predicted Q3 2026 yield % |
| yield_direction_next_q | int (0/1) | **Target**: 1 = yield rises next quarter |
| risk_adjusted_yield | float | **Target**: agg_current / volatility_current |
| outperformance_vs_market_pp | float | **Target**: Change pp vs market average |
| investment_score | float | **Target**: Composite 0–100 investment attractiveness |

---

## Derived Feature Engineering

These features are computed by `blocks_agents/handlers/feature_engineering_expert.py` from the source columns below. They are derived research inputs, not independent observations or validated investment signals.

| Feature | Formula | Source fields | Interpretation |
|---|---|---|---|
| `yield_momentum` | `yield_trend_slope * yield_volatility` | `yield_trend_slope`, `yield_volatility` | Trend strength scaled by yield variability. |
| `mcap_to_tvl` | `mcap_end_current_usd / tvl_usd` | `mcap_end_current_usd`, `tvl_usd` | Market-cap-to-TVL ratio; undefined when TVL is zero. |
| `risk_score` | `beta_vs_btc * volatility_annualized_current / sharpe_ratio_current` | `beta_vs_btc`, `volatility_annualized_current`, `sharpe_ratio_current` | Combined systematic/volatility pressure scaled by current Sharpe; undefined when Sharpe is zero. |
| `yield_premium` | `agg_current - yield_vs_category_avg` | `agg_current`, `yield_vs_category_avg` | Current aggregate yield relative to the stored category-relative metric; verify the metric's definition before interpreting as a peer premium. |

Zero denominators are represented as `null` with a warning rather than silently converted to zero. Because both yield source files conflict, always record `source_file` and do not treat the two versions as independent observations.

## Model Training Suggestions

### Regression Tasks
- Predict `q3_26_forward_yield` from: yield history + price momentum + volatility + yield_trend_slope
- Predict `risk_adjusted_yield` from: sharpe_ratio + beta + yield + volatility

### Classification Tasks
- Predict `yield_direction_next_q` from: yield_trend_slope + momentum_90d + rsi_14d + volume_trend
- Classify `investment_score` buckets (buy/hold/avoid) from composite features

### Feature Engineering Ideas
- `yield_momentum = yield_trend_slope * yield_volatility`
- `mcap_to_tvl = mcap_end_current_usd / tvl_usd`
- `risk_score = beta_vs_btc * volatility_annualized_current / sharpe_ratio_current`
- `yield_premium = agg_current - yield_vs_category_avg`
