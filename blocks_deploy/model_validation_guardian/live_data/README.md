# Live market and blockchain overlay

This directory is a **separate current-data overlay**. It never replaces the historical `yield_data.csv` source used by handlers and models.

## What is collected

`live_worker.py` collects one best-effort cycle for canonical symbols:

- Binance public `/api/v3/ticker/24hr` batch market data (primary price, 24-hour change, quote volume).
- Coinbase Exchange public `/products/<product>/stats` for BTC, ETH, and SOL (secondary comparison/fallback).
- DeFiLlama `/v2/chains` chain TVL observations.
- EVM `eth_blockNumber` and Solana `getEpochInfo` JSON-RPC health observations.

Every observation includes provider, endpoint, and `observed_at`. The snapshot includes provider errors and the configured stale threshold. Empty or failed observations are not converted into zeroes.

## Rate-limit policy

The worker uses one provider limiter per process, batches Binance symbols, polls Coinbase only for a small independent sample, caches results on disk, retries only transient failures with jitter, and waits at least two seconds between DeFiLlama/RPC calls. Its default five-minute cycle is intentionally much slower than the providers' documented public limits. Do not run multiple copies behind the same public IP without coordinating their budgets.

Provider documentation should be rechecked before changing intervals:

- Binance Spot REST: <https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market> and <https://github.com/binance/binance-spot-api-docs>
- Coinbase Exchange: <https://docs.cdp.coinbase.com/exchange/rest-api/rate-limits>
- DeFiLlama API: <https://api-docs.defillama.com/> and <https://docs.llama.fi/pro-api>
- CoinGecko documentation (optional future keyed enrichment): <https://docs.coingecko.com/docs/errors-and-rate-limits>
- Solana RPC guidance: <https://solana.com/rpc>

The current implementation does not require API keys. Optional provider URLs can be injected through environment variables; use dedicated/keyed RPC or provider plans for sustained production traffic rather than relying on shared public endpoints.

## Files and freshness

- `live_snapshot.json` — generated atomic snapshot; ignored by Git.
- `worker_status.json` — generated health/status record; ignored by Git.
- `live_snapshot.example.json` — committed schema example only.
- `schema_version=live-overlay-1` and `data_status=live_overlay_only` identify the boundary.
- Default stale threshold is 900 seconds. Consumers must display stale/unavailable status and must not treat stale values as live.

## Run continuously

Local:

```bash
python live_worker.py
```

Container supervisor:

```bash
docker compose -f docker-compose.live.yml up -d --build
cat live_data/worker_status.json
```

The Compose service uses `restart: unless-stopped`, a non-root user, an init process, an atomic output volume, and a healthcheck. A real production deployment should add host monitoring, alerting, persistent volume backups as appropriate, and a dedicated egress/network policy.

The worker mirrors current snapshots into each data-consuming `blocks_deploy/*/live_data/` directory. This is convenience enrichment only. Paid Blocks handlers remain historical-source-first and never dispatch network calls from a task.

## Safety boundary

Live values are market context, not yield observations, validated forecasts, or investment advice. Provider timestamps, errors, and freshness must remain visible in UI/API artifacts. If all providers fail, the previous snapshot is retained and worker status becomes `degraded`; an empty feed is never presented as a successful update.
