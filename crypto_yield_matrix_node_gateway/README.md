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
LLM_DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
LLM_HOSTED_BASE_URL=
LLM_HOSTED_ALLOWED_HOSTS=
LLM_TIMEOUT_MS=120000
LLM_MAX_RESPONSE_BYTES=1000000
LLM_MAX_CONCURRENT=2
LLM_MAX_REQUESTS_PER_MINUTE=10
```

`GATEWAY_CLIENT_KEYS` contains caller credentials in `clientId=secret` form. Use a different secret from the Blocks API key. Secrets are compared in constant time and are never logged. `GATEWAY_CLIENT_AGENTS` can restrict each caller to named agents; omit it only for a trusted single-tenant gateway. The default listener is loopback-only; every non-loopback bind requires `GATEWAY_ALLOW_PUBLIC_BIND=true` and must sit behind a verified private, TLS-terminating authenticated edge. This built-in ledger is intentionally single-instance and persisted at `GATEWAY_BUDGET_STATE_FILE`; the supplied Compose file mounts a durable volume. Run one gateway instance unless an external shared quota ledger is added. Providers can scale independently through Blocks runtime settings.

The gateway reserves a task before calling Blocks. The reservation is conservative: uncertain, failed, or canceled remote outcomes still consume the configured daily allowance so a network ambiguity cannot cause uncontrolled spend. Create the configured kill-switch file to stop new paid dispatches immediately. Responses include remaining task/spend budget headers and a release identifier. `X-Gateway-Schema-Version: 1` is the current optional request contract marker. Artifact count and declared/downloaded byte limits prevent unbounded response growth; artifacts with missing/over-limit declared sizes are not downloaded, and incomplete artifact retrieval returns HTTP 502 with `artifactStatus: "partial"` rather than looking like a complete success. The `X-Idempotency-Key` header is forwarded to Blocks for caller retries; the gateway itself never retries an uncertain paid send.

## Endpoints

- `GET /health` — no-spend liveness.
- `GET /ready` — no-spend configuration, kill-switch, and daily-budget readiness.
- `GET /agents` — served agent catalog.
- `GET /metrics` — authenticated no-spend process counters for request status, auth rejection, accepted/completed/failed invokes, rate/budget/capacity/kill-switch/artifact rejection, and timeouts; it requires the gateway bearer credential and should still be restricted to a trusted operational network.
- `POST /agents/:agentName/invoke` — requires `Authorization: Bearer <gateway-client-secret>` and JSON containing a non-empty `question`; this is the paid Blocks path.
- `POST /llm/chat` — requires the same gateway credential and uses local Ollama by default. Set `provider: "hosted"` only when the operator has configured `LLM_HOSTED_BASE_URL`; pass a transient user key with `X-LLM-API-Key`.

Example:

```bash
curl -s http://localhost:3000/agents/crypto_risk_analyst/invoke \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer YOUR_GATEWAY_CLIENT_SECRET' \
  -H 'x-idempotency-key: btc-risk-001' \
  -d '{"question":"Compare BTC yield and downside context","symbol":"BTC","source_file":"yield_data.csv"}'
```

Responses include an `x-request-id` correlation header and task results include the same `requestId`. Logs are structured JSON and exclude payloads and secrets. `/metrics` is an authenticated lightweight local baseline; ship it and the structured logs to centralized monitoring before production or horizontal scaling.

## LLM chat

Ollama is the default local backend at `OLLAMA_BASE_URL` with model `OLLAMA_MODEL`. The gateway uses `POST /api/chat` with `stream: false`; install and pull a model locally, for example `ollama pull llama3.2:3b`. Ollama normally has no local authentication, so keep it on loopback or behind a private authenticated network.

Hosted inference is deliberately operator-configured rather than an arbitrary URL supplied by callers. Set `LLM_HOSTED_BASE_URL` to an HTTPS OpenAI-compatible provider endpoint and list its hostname in `LLM_HOSTED_ALLOWED_HOSTS`. The gateway performs a DNS preflight and rejects private/link-local/metadata destinations; for public production, use a fixed egress proxy or network policy as the authoritative SSRF boundary because DNS can change between preflight and connection. Users may send their own key per request. LLM calls have independent per-client rate and concurrency limits and a bounded response size:

```bash
curl -s http://localhost:3000/llm/chat \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer YOUR_GATEWAY_CLIENT_SECRET' \
  -H 'x-llm-api-key: USER_HOSTED_LLM_KEY' \
  -d '{"provider":"hosted","model":"your-model","messages":[{"role":"user","content":"Summarize the BTC risk context."}]}'
```

User keys are used only for the outbound request; they are not persisted, returned, or logged. The gateway rejects hosted mode when no operator URL, allowlisted hostname, or per-request key is available. Invalid requests return 400, upstream failures return 502, and timeouts return 504. LLM calls are separate from the paid Blocks task budget, so configure a provider-side quota or a gateway-level LLM quota before public exposure.

## Local validation (no paid calls)

```bash
npm install
npm run check
npm run smoke
npm run resilience
npm run llm-smoke
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
