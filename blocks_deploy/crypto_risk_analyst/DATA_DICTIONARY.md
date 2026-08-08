# Yield Data Dictionary — cryptocurrentcy Underlying Asset Cash Yield Matrix
**Version:** 2.0 Production | **Assets:** 59 | **Features:** 118 | **Date:** 2026-08-06

---

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

## NEW: Market Size Features (7 columns)
| Column | Type | Description |
|--------|------|-------------|
| mcap_rank | int | Rank by market cap (1 = largest) |
| mcap_percentile | float | Percentile rank by market cap (0–100) |
| is_large_cap | int (0/1) | Market cap ≥ $10B |
| is_mid_cap | int (0/1) | Market cap $1B–$10B |
| is_small_cap | int (0/1) | Market cap < $1B |
| mcap_to_tvl_ratio | float | Market cap / TVL (valuation efficiency) |
| volume_to_mcap_ratio | float | 24h volume / market cap (liquidity depth) |

## NEW: Price Momentum Features (3 columns)
| Column | Type | Description |
|--------|------|-------------|
| price_momentum_1y | float | Full-year price change % (prior start to current end) |
| is_above_50d_ma | int (0/1) | Price above 50-day moving average |
| trend_strength | float | Absolute MA50/200 cross distance |

## NEW: Yield Quality Features (7 columns)
| Column | Type | Description |
|--------|------|-------------|
| yield_consistency | float | 1 / (1 + yield_volatility), higher = more stable |
| yield_momentum | float | yield_trend_slope × yield_volatility |
| yield_acceleration | float | Quarterly yield acceleration (change_pp / 4) |
| yield_vs_market_avg | float | Yield minus cross-sectional market average |
| yield_percentile | float | Percentile rank of yield (0–100) |
| yield_to_vol_ratio | float | Yield / annualized volatility (income per unit risk) |
| yield_to_drawdown_ratio | float | Yield / max drawdown (income per unit tail risk) |

## NEW: Risk-Adjusted Performance (6 columns)
| Column | Type | Description |
|--------|------|-------------|
| sortino_ratio | float | Yield / downside deviation proxy |
| calmar_ratio | float | Yield / max drawdown |
| treynor_ratio_btc | float | Yield / beta_vs_btc |
| treynor_ratio_eth | float | Yield / beta_vs_eth |
| information_ratio | float | Outperformance / tracking error (yield vol) |
| omega_ratio_proxy | float | (Yield + 5) / max drawdown (gain/loss asymmetry) |

## NEW: Portfolio Construction (4 columns)
| Column | Type | Description |
|--------|------|-------------|
| diversification_score | float | Lower correlation = higher diversification (0–100) |
| systematic_risk_pct | float | Beta² × 100 (% of risk from market) |
| idiosyncratic_risk_pct | float | 100 – systematic_risk_pct (% of risk unique to asset) |
| tail_risk_score | float | Max drawdown / volatility (tail event severity) |

## NEW: On-Chain Health (4 columns)
| Column | Type | Description |
|--------|------|-------------|
| network_value_to_tx | float | Market cap / daily transactions (NVT proxy) |
| addr_per_mcap | float | Active addresses per $1M market cap |
| tx_velocity | float | Daily transactions / circulating supply (turnover) |
| supply_liquidity_ratio | float | Circulating supply / 24h volume (liquidity depth) |

## NEW: Tokenomics Features (5 columns)
| Column | Type | Description |
|--------|------|-------------|
| supply_inflation_adjusted_yield | float | Yield minus inflation rate (real yield) |
| is_deflationary | int (0/1) | Negative inflation rate |
| is_high_inflation | int (0/1) | Inflation rate > 8% |
| fdv_premium | float | (FDV/mcap – 1) × 100 (dilution risk premium) |
| scarcity_score | float | 0–100, higher = lower dilution risk |

## NEW: Technical Regime (8 columns)
| Column | Type | Description |
|--------|------|-------------|
| is_overbought | int (0/1) | RSI > 70 |
| is_oversold | int (0/1) | RSI < 30 |
| golden_cross | int (0/1) | MA50 > MA200 |
| death_cross | int (0/1) | MA50 < MA200 by >10% |
| bull_market_proxy | int (0/1) | Momentum > 20% AND RSI > 50 |
| bear_market_proxy | int (0/1) | Momentum < –20% AND RSI < 40 |
| high_vol_regime | int (0/1) | Volatility > 80% |
| low_vol_regime | int (0/1) | Volatility < 50% |

## NEW: Composite Scores (4 columns)
| Column | Type | Description |
|--------|------|-------------|
| quality_score | float | Sharpe + consistency + diversification + drawdown |
| value_score | float | Yield percentile + mcap percentile + real yield + category premium |
| momentum_score | float | Price momentum + yield trend + volume trend + price change |
| risk_score | float | Drawdown + volatility + beta + tail risk (higher = riskier) |

## NEW: Advanced Prediction Targets (5 columns)
| Column | Type | Description |
|--------|------|-------------|
| yield_regime | string | low / medium / high / very_high (binned yield) |
| risk_regime | string | low / medium / high / extreme (binned volatility) |
| expected_return_1y | float | Model-implied 1-year expected return % |
| expected_max_drawdown | float | Model-implied worst-case drawdown % |
| probability_positive_return | float | Estimated probability of positive return (1–99%) |

## NEW: ML Pipeline (3 columns)
| Column | Type | Description |
|--------|------|-------------|
| ml_fold | string | train / val / test split indicator |
| ml_weight | float | Sample weight for weighted training (0.8–1.2) |
| data_quality_flag | int | 0=clean, 1=annualized, 2=extreme_vol, 3=suspicious_sharpe |

## NEW: Rankings (3 columns)
| Column | Type | Description |
|--------|------|-------------|
| sharpe_rank | int | Rank by Sharpe ratio (1 = best) |
| risk_adj_yield_rank | int | Rank by risk-adjusted yield (1 = best) |
| calmar_rank | int | Rank by Calmar ratio (1 = best) |

---

## Model Training Suggestions

### Regression Tasks
- **Predict `q3_26_forward_yield`** from: yield history + price momentum + volatility + yield_trend_slope + yield_consistency
- **Predict `risk_adjusted_yield`** from: sharpe_ratio + beta + yield + volatility + calmar_ratio
- **Predict `investment_score`** from: quality_score + value_score + momentum_score – risk_score

### Classification Tasks
- **Predict `yield_direction_next_q`** from: yield_trend_slope + momentum_90d + rsi_14d + volume_trend + yield_acceleration
- **Classify `yield_regime`** (4-class) from: agg_current + yield_vs_category_avg + supply_inflation_adjusted_yield + category
- **Classify `risk_regime`** (4-class) from: volatility + beta + max_drawdown + tail_risk_score

### Feature Engineering Ideas
- `yield_momentum = yield_trend_slope × yield_volatility`
- `mcap_to_tvl = mcap_end_current_usd / tvl_usd`
- `risk_efficiency = yield_to_vol_ratio / beta_vs_btc`
- `value_momentum = value_score × momentum_score`
- `quality_risk = quality_score / (1 + risk_score)`

### Production Pipeline Notes
- Use `data_quality_flag` to filter or weight samples
- Use `ml_fold` for cross-validation (47 train / 7 val / 5 test)
- Use `ml_weight` for sample-weighted loss functions
- `is_annualized` assets (XRP, XLM, ONDO, WLD) have lower confidence — consider separate model
- All prices validated against mcap × supply (consistency < 1% for top assets)
