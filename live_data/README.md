# Live market and blockchain overlay

This directory is a **separate current-data overlay**. It never replaces the historical `yield_data.csv` source used by handlers and models.

## What is collected

`live_worker.py` collects one best-effort cycle for canonical symbols:

- Binance public `/api/v3/ticker/24hr` batch market data (primary price, 24-hour change, quote volume).
- Coinbase Exchange public `/products/<product>/stats` for BTC, ETH, and SOL (secondary comparison/fallback).
- DeFiLlama `/v2/chains` chain TVL observations.
- EVM `eth_blockNumber` and Solana `getEpochInfo` JSON-RPC health observations.

Every observation includes provider, provider coverage, endpoint, and `observed_at`. Each provider status includes the last HTTP status and sanitized rate-limit headers when supplied. The snapshot includes provider errors and the configured stale threshold. Empty or failed observations are not converted into zeroes. Coinbase is currently only a secondary/fallback sample for BTC, ETH, and SOL; most other assets are explicitly single-provider observations.

## Controlled provider canary

Run the safe fixture canary locally:

```bash
python live_canary.py --fixture
```

It records a JSON evidence envelope at `live_data/provider_canary_evidence.json` with UTC start/end timestamps, per-request timestamps, endpoint, HTTP status, latency, schema validation, selected rate-limit headers, and sanitized errors. The fixture never contacts a provider. A live canary is deliberately opt-in:

```bash
python live_canary.py --live --confirm-live --output live_data/provider_canary_evidence.json
```

Before a live run, an accountable operator must review the current provider terms, attribution requirements, endpoint schemas, polling limits, and approved egress/IP. The tool does not certify those terms and no live canary result is present in this repository.

## Provider terms, attribution, and polling policy

Reconfirm these official pages immediately before production and retain the reviewed date, terms version/page, attribution decision, and approved polling budget in the release record:

- Binance Spot REST: <https://developers.binance.com/en/docs/products/spot/rest-api> and <https://github.com/binance/binance-spot-api-docs>. Respect request-weight headers, HTTP 429 responses, and IP bans.
- Coinbase Exchange: <https://docs.cdp.coinbase.com/exchange/rest-api/rate-limits>. Respect public IP token-bucket limits and HTTP 429 responses.
- DeFiLlama: <https://api-docs.defillama.com/>, <https://docs.llama.fi/pro-api>, and <https://defillama.com/terms>. Do not scrape non-public endpoints; use an approved plan for sustained commercial traffic.
- Cloudflare Ethereum Gateway: <https://developers.cloudflare.com/web3/reference/limits/> and <https://developers.cloudflare.com/web3/ethereum-gateway/>. Confirm the selected plan's quotas and terms.
- Solana RPC: <https://solana.com/rpc> and <https://solana.com/docs/references/clusters>. Shared public RPC is best effort and not a production SLA; use an approved dedicated provider for sustained traffic.

The worker uses one provider limiter per process, batches Binance symbols, polls Coinbase only for a small independent sample, retries only transient failures with jitter, and waits at least two seconds between DeFiLlama/RPC calls. Its default five-minute cycle is intentionally conservative. Do not run multiple copies behind the same public IP without coordinating budgets.

## Files, distribution, and freshness

- `live_snapshot.json` — generated atomic snapshot; ignored by Git.
- `worker_status.json` — generated status record; ignored by Git.
- `provider_canary_evidence.json` — generated canary evidence; ignored by Git.
- `live_snapshot.example.json` — committed schema example.
- `worker_status.example.json` — liveness/readiness example.
- `distribution_contract.json` — required volume/distribution contract.
- `schema_version=live-overlay-1` and `data_status=live_overlay_only` identify the boundary.
- Default stale threshold is 900 seconds. Consumers must display stale/unavailable status and must not treat stale values as live.

Local mirroring writes the same snapshot atomically to `blocks_deploy/<agent>/live_data/live_snapshot.json` for all 11 data-consuming deployments. For containers, mount one managed volume at `/app/live_data` in the worker and mount it read-only in every consumer. Hosted Blocks runtimes cannot see a local Docker volume: use an approved object-store, sidecar, or deployment-sync mechanism preserving the same filenames and atomic replacement. See `distribution_contract.json`.

## Liveness versus data readiness

These are intentionally separate:

- **Liveness:** `worker_status.json.liveness` is `running` when the worker process is cycling and `stopped` otherwise.
- **Data readiness:** `fresh_observations` requires current observations without provider errors; `degraded` means some data exists but the cycle has errors; `no_fresh_observation` means no current observation is usable.

Alert separately: page on worker liveness failure or an old `last_cycle_at`; warn/page on `degraded` or `no_fresh_observation`; never promote retained observations to fresh. The worker status is not proof of provider terms, Blocks health, A2A grants, or paid billing.

## Run continuously

```bash
python live_worker.py
# or
docker compose -f docker-compose.live.yml up -d --build
cat live_data/worker_status.json
```

The Compose service uses `restart: unless-stopped`, an init process, an atomic output volume, and a healthcheck. A real production deployment still needs host monitoring, centralized alerting, backups, a dedicated egress/network policy, and an accountable operator.

## Safety boundary

Live values are market context, not yield observations, validated forecasts, or investment advice. Provider timestamps, status, headers, errors, and freshness must remain visible in UI/API artifacts. If all providers fail, the previous snapshot is retained and worker status becomes degraded; an empty feed is never presented as a successful update. Paid Blocks handlers remain historical-source-first and never dispatch provider network calls from a task.
