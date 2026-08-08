# Crypto Yield Matrix

## Stop chasing headline APY. Start seeing the whole opportunity.

Crypto yield is easy to find—and surprisingly hard to understand.

One screen says **12%**. Another hides a **70% drawdown**. A third shows a “market” number with no timestamp, no provenance, and no explanation of whether the return comes from staking, inflation, lending, fees, or a temporary incentive.

**Crypto Yield Matrix turns that noise into a research workflow you can actually use.**

It brings 59 crypto assets, eight quarters of yield history, risk context, liquidity signals, tokenomics, market snapshots, and specialist AI analysis into one evidence-first workspace.

Not another APY leaderboard.

A faster way to answer the questions that matter:

- Is the yield improving—or simply getting louder?
- What changed between the prior and current window?
- Is the reward mechanism comparable to the next asset?
- Can the market context support the story?
- Which claims are backed by a supplied quote snapshot, and which require fresh verification?
- What should I investigate next before making a decision?

## The moment it clicks

Open the matrix and the market stops looking like a list of isolated percentages.

You see the movement across quarters. You see prior versus current 12-month aggregates. You see percentage-point change. You see methodology notes, risk-adjusted context, liquidity signals, and transparent data coverage.

Hover an asset. Search a category. Filter to quote-backed assets. Sort by current yield, yield change, investment score, or market cap. Export the exact shortlist you want to review.

The result is not more data.

It is **less wasted attention**.

## What you get

### 1. The Yield Matrix

A visual eight-quarter map of annualized yield across the tracked universe.

- Prior and current windows separated for instant comparison.
- Each quarter sorted by descending yield.
- 12-month aggregate columns with directional change in percentage points.
- Annualization markers and methodology notes for unlike reward mechanisms.
- Focus view for key assets plus the full 59-asset explorer.

See the trend before you commit to the headline.

### 2. The All-Asset Explorer

Every canonical asset gets a consistent research card—even when the supplied market data is incomplete.

Search by symbol, name, or category. Filter by source coverage. Filter by quote availability. Sort by:

- Current aggregate yield.
- Yield change versus the prior window.
- Investment score from the supplied matrix.
- Market-cap context.

No asset disappears because its evidence is imperfect. Instead, the interface tells you exactly what is available and what still needs verification.

### 3. Yahoo-style quote exports for every asset

Need a spreadsheet? Need a handoff? Need one file per asset?

The system generates a uniform quote-style CSV for all 59 canonical symbols under `csv/quotes/<SYMBOL>.csv`.

Each export uses the same familiar market-data shape as the supplied Yahoo/CoinMarketCap-style tables, including fields such as:

- Market price and change.
- Open, high, low, previous close.
- Volume and average volume.
- Market cap and fully diluted value.
- Circulating, maximum, and total supply.
- 52-week range and moving averages.
- Website, whitepaper, logo, exchange, and source metadata.

Every file also carries the fields a trustworthy workflow needs:

- `quote_status` — `source_snapshot` or `unavailable`.
- `quote_source_file` — exact supplied table used.
- `quote_as_of_iso` — quote timestamp when provided.
- `quote_completeness_pct` — how much of the normalized quote schema was supplied.
- `yield_matrix_symbol` — the joined canonical asset.
- `yield_current_aggregate_pct` and `yield_change_pp` — the yield context.

For the 9 assets with supplied market snapshots, quote fields are preserved. For the other 50, the same file exists with honest blanks—not fabricated prices, stale-looking zeros, or invented “live” values.

Uniform exports. Explicit gaps. Zero guesswork.

### 4. Decision-ready derived features

The catalog materializes transparent research aids that can be audited back to their inputs:

- `yield_momentum` — yield trend slope × yield volatility.
- `mcap_to_tvl` — market cap divided by TVL where both are available.
- `risk_score` — beta × current volatility ÷ current Sharpe-like measure.
- `yield_premium` — current aggregate yield minus the category-average gap.

These features help prioritize research. They are not magic scores, hidden model outputs, or promises of returns.

### 5. Evidence-first AI specialists

Instead of asking one generic assistant to improvise, the fleet separates the work:

- **Risk analyst** — yield beside volatility, drawdown, beta, and risk-adjusted measures.
- **Liquidity analyst** — volume, TVL, addresses, transactions, and exit-risk questions.
- **Tokenomics expert** — inflation, dilution, supply, FDV, and sustainability context.
- **Yield methodology expert** — staking, lending, annualization, lockups, and comparability.
- **Feature engineer** — reproducible formulas and missing-denominator warnings.
- **Portfolio scenario expert** — explicit trade-offs under user constraints.
- **Provenance auditor** — source lineage, duplicate rows, and data-quality questions.
- **Model validation guardian** — leakage, split design, repeated provenance, and overclaiming.
- **Matrix insights agent** — turns the visual matrix into traceable findings.
- **Research communications agent** — makes the result clear without disguising uncertainty.
- **Quant forecasting expert** — designs the path to a validated forecast while keeping the safety gate closed today.

The orchestrator can merge specialist perspectives while preserving partial failures and provenance.

### 6. Research guidance built into every result

Every artifact answers three practical questions:

1. **How can I use this?**
2. **What should I review next?**
3. **What must I not infer?**

That means the output does not stop at “SOL is 7.08%.” It continues with the context needed to interpret that number—and the next check needed before relying on it.

### 7. One-click shortlist export

Find a pattern. Filter the universe. Download the shortlist.

The browser export preserves the fields currently visible in the catalog, including yield, change, score, category, quote status, timestamps, and provenance. It is built for analysts, investment committees, research notes, and repeatable handoffs.

## Designed for the real questions

### For crypto investors

Cut through APY theater. Compare reward levels with drawdown, inflation, volatility, market-cap context, and quote coverage before putting a number in front of a decision.

### For researchers

Start with a stable 59-asset universe, eight-quarter history, row-level provenance, reproducible derived fields, and exportable evidence.

### For protocols and treasury teams

Benchmark yield mechanisms, identify category shifts, inspect sustainability questions, and prepare a cleaner research brief for internal review.

### For product and data teams

Use a consistent catalog schema, per-asset files, quote metadata, explicit missingness, validation scripts, and Blocks-compatible specialist artifacts.

## The trust advantage

Crypto research earns attention when it is exciting. It earns confidence when it is traceable.

Crypto Yield Matrix makes the boundary visible:

- `yield_data.csv` remains the single canonical handler source.
- Generated catalogs never replace primary evidence.
- Quote snapshots show their source and timestamp.
- Missing values remain blank and visible.
- Repeated provenance rows are not silently treated as independent observations.
- Forecasting remains blocked until dated history and out-of-time validation exist.
- Results are decision support—not financial advice, guaranteed returns, or live-market claims.

That is not friction.

That is what makes the output usable in a serious conversation.

## A better first five minutes

**Minute 1 — Scan:** See the yield matrix and prior/current movement.  
**Minute 2 — Narrow:** Search a symbol or filter a category.  
**Minute 3 — Verify:** Check quote status, timestamp, methodology, and risk context.  
**Minute 4 — Ask:** Send the asset to the right specialist—risk, liquidity, tokenomics, or methodology.  
**Minute 5 — Export:** Download the shortlist and carry the evidence into your next review.

Five minutes to move from “this yield looks interesting” to “here is what I know, here is what I do not know, and here is the next question.”

## Built to grow without losing the plot

The architecture is ready for a richer evidence pipeline:

- Add new dated quote snapshots without changing the canonical yield contract.
- Refresh source-backed exports with timestamps and hashes.
- Expand per-asset history while preserving the same file shape.
- Add scenario sensitivity for fees, lockups, inflation, drawdown, and slippage.
- Promote forecasting only after walk-forward validation and independent outcomes.
- Serve the specialist fleet through a protected, paid Blocks gateway with quotas and spend controls.

## Start with the matrix

You do not need another dashboard that makes every asset look equally certain.

You need a research system that shows the signal, the context, the source, the gap, and the next move.

**Explore the matrix. Find the opportunity. Verify the story.**

### Important note

The current market quote exports are snapshots from the supplied source tables, not a live market feed. The canonical yield dataset contains historical/provenance-labeled data and is not a guarantee of future performance. Always verify current prices, liquidity, fees, lockups, reward composition, and protocol conditions before acting. This product provides research and decision-support artifacts, not financial advice.
