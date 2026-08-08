# Crypto Yield Matrix Node Gateway

A single server-side Node.js consumer for the 12 published Crypto Yield Matrix agents. Every dispatched task uses the Blocks SDK with `billingMode: 'paid'`; the gateway never exposes `BLOCKS_API_KEY` to callers.

## Secure configuration

Copy the repository template into the deployment secret manager or local ignored `.env`:

```dotenv
BLOCKS_API_KEY=server_side_blocks_key
GATEWAY_CLIENT_KEYS=research_app=replace_with_a_random_secret_at_least_16_chars
GATEWAY_CLIENT_AGENTS=research_app=crypto_risk_analyst|matrix_research_insights_agent
GATEWAY_MAX_DAILY_TASKS=100
GATEWAY_MAX_DAILY_SPEND_USD=10
GATEWAY_TASK_COST_USD=0.10
GATEWAY_HOST=127.0.0.1
GATEWAY_ALLOW_PUBLIC_BIND=false
GATEWAY_RELEASE_ID=release-or-image-digest
GATEWAY_MAX_REQUESTS_PER_MINUTE=30
GATEWAY_MAX_CONCURRENT_TASKS=8
GATEWAY_MAX_ARTIFACT_BYTES=5242880
GATEWAY_MAX_ARTIFACT_COUNT=32
GATEWAY_BUDGET_STATE_FILE=.gateway-state/budget.json
GATEWAY_KILL_SWITCH_FILE=.gateway-state/PAUSE_PAID_TASKS
```

`GATEWAY_CLIENT_KEYS` contains caller credentials in `clientId=secret` form. Use a different secret from the Blocks API key. Secrets are compared in constant time and are never logged. `GATEWAY_CLIENT_AGENTS` can restrict each caller to named agents; omit it only for a trusted single-tenant gateway. The default listener is loopback-only; every non-loopback bind requires `GATEWAY_ALLOW_PUBLIC_BIND=true` and must sit behind a verified private, TLS-terminating authenticated edge. This built-in ledger is intentionally single-instance and persisted at `GATEWAY_BUDGET_STATE_FILE`; the supplied Compose file mounts a durable volume. Run one gateway instance unless an external shared quota ledger is added. Providers can scale independently through Blocks runtime settings.

The gateway reserves a task before calling Blocks. The reservation is conservative: uncertain, failed, or canceled remote outcomes still consume the configured daily allowance so a network ambiguity cannot cause uncontrolled spend. Create the configured kill-switch file to stop new paid dispatches immediately. Responses include remaining task/spend budget headers and a release identifier. `X-Gateway-Schema-Version: 1` is the current optional request contract marker. Artifact count and declared/downloaded byte limits prevent unbounded response growth; over-limit artifacts are reported explicitly rather than silently dropped. The `X-Idempotency-Key` header is forwarded to Blocks for caller retries; the gateway itself never retries an uncertain paid send.

## Endpoints

- `GET /health` — no-spend liveness.
- `GET /ready` — no-spend configuration, kill-switch, and daily-budget readiness.
- `GET /agents` — served agent catalog.
- `GET /metrics` — authenticated no-spend process counters for request status, auth rejection, accepted/completed/failed invokes, rate/budget/capacity/kill-switch/artifact rejection, and timeouts; it requires the gateway bearer credential and should still be restricted to a trusted operational network.
- `POST /agents/:agentName/invoke` — requires `Authorization: Bearer <gateway-client-secret>` and JSON containing a non-empty `question`.

Example:

```bash
curl -s http://localhost:3000/agents/crypto_risk_analyst/invoke \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer YOUR_GATEWAY_CLIENT_SECRET' \
  -H 'x-idempotency-key: btc-risk-001' \
  -d '{"question":"Compare BTC yield and downside context","symbol":"BTC","source_file":"yield_data.csv"}'
```

Responses include an `x-request-id` correlation header and task results include the same `requestId`. Logs are structured JSON and exclude payloads and secrets. `/metrics` is an authenticated lightweight local baseline; ship it and the structured logs to centralized monitoring before production or horizontal scaling.

## Local validation (no paid calls)

```bash
npm install
npm run check
npm run smoke
npm run resilience
```

The smoke test uses placeholder credentials and never dispatches to Blocks.

## Container operation

The included `Dockerfile` runs the gateway as the non-root `node` user. `docker-compose.yml` adds restart supervision, localhost-only binding by default, runtime `.env` injection, and a `/ready` health check:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f gateway
```

Put the gateway behind an authenticated reverse proxy before allowing external access. Do not publish port 3000 directly to the Internet. Use centralized secret management, structured log shipping, alerting, and a shared quota service before operating multiple gateway replicas.
