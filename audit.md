# Production Readiness Audit

**Project:** Crypto Yield Matrix / Blocks.ai agent fleet
**Audit date:** 2026-08-07
**Update:** Post-remediation repository audit
**Verdict:** **CONDITIONAL PRIVATE PILOT — NO-GO for public or unattended paid production**

## Executive summary

The repository-controlled blockers identified in the original audit have been addressed in code and documentation. The Node gateway now requires separate caller authentication, supports per-client agent allowlists, enforces rate and daily paid-task budgets, persists the single-instance budget ledger, validates the canonical data source, emits request-correlated structured logs, and provides no-spend health/readiness endpoints. The gateway remains compatible with the Blocks consumer `TaskClient`, paid `billingMode`, forwarded idempotency keys, native provider cards, and server-side `BLOCKS_API_KEY` handling.

The canonical data contract is now explicit: `yield_data.csv` contains 118 rows, 59 unique symbols, 61 columns, 59 analytical columns, and two provenance columns. The dictionary distinguishes current CSV fields from planned/derived fields, and `audit_csv.py` checks that every CSV field is documented. Stale multi-source setup instructions were removed, deployment dictionary copies were synchronized, and the forecasting safety gate remains intact.

The project is now suitable for a **controlled private pilot** behind a supervised single gateway instance after external Blocks validation. It is still not ready for public exposure or unattended paid production until the live Blocks registry, provider connectivity, A2A permissions, secret-management controls, centralized observability, and a budgeted paid canary are verified.

## Implemented remediation

### Gateway security and paid-task safety

- Added `Authorization: Bearer <gateway-client-secret>` authentication for paid invocation.
- Kept gateway caller secrets separate from the server-side `BLOCKS_API_KEY`.
- Compared secrets with constant-time comparison and reject client secrets equal to the Blocks key.
- Added optional per-client agent allowlists through `GATEWAY_CLIENT_AGENTS`.
- Added per-client rolling request limits.
- Added conservative UTC-day task and spend budgets.
- Persisted the budget ledger through an atomic JSON state write for the single gateway instance.
- Preserved Blocks `billingMode: 'paid'` and forwarded `X-Idempotency-Key` behavior.
- Kept application retries disabled after uncertain paid sends.
- Added canonical `source_file` validation at the gateway boundary.
- Added question-length and JSON content-type validation.

The budget is intentionally conservative: a task reservation remains counted even if a remote result is uncertain, failed, or canceled. This prevents ambiguous network outcomes from creating uncontrolled spend. The persisted ledger is single-instance protection, not a distributed quota service; do not horizontally scale gateways without replacing it with shared durable accounting.

### Operations and observability

- Added request IDs through the `X-Request-Id` header and response body/result.
- Added structured JSON request-completion and rejection logs without request payloads or secrets.
- Added `/health` for no-spend liveness and `/ready` for no-spend client/budget readiness.
- Added a non-root `Dockerfile`.
- Added supervised single-instance `docker-compose.yml` with restart policy, localhost-only binding by default, runtime environment injection, and readiness health checks.
- Added Docker build exclusions for secrets, dependencies, logs, and local state.
- Documented secret rotation, caller credentials, budgets, private-network operation, and the single-gateway topology.

### Data and user-value improvements

- Reconciled `DATA_DICTIONARY.md` with the actual 61-column CSV contract.
- Documented `source_file` and `source_row` as provenance columns.
- Clearly labeled the later feature sections as planned/derived fields rather than current observed CSV columns.
- Added dictionary field coverage checks to `audit_csv.py`.
- Removed stale instructions about a second independent dataset.
- Kept row-level provenance in research evidence so duplicate symbols remain explainable.
- Preserved explicit uncertainty and non-advisory language.
- Kept forecasting blocked until dated history and out-of-time validation exist.

## Evidence and no-spend validation

The following checks pass after remediation:

| Check | Result |
|---|---|
| Canonical CSV audit | Pass: 118 rows, 61 columns, 0 issues |
| Dictionary field coverage | Pass through `audit_csv.py` |
| Deployment CSV mirrors | Pass: 11 copies byte-identical to root |
| Deployment dictionary mirrors | Pass: 11 copies byte-identical to root |
| Python compilation | Pass for `blocks_agents` and `blocks_deploy` |
| A2A orchestrator mocked tests | Pass |
| JSON parsing | Pass for repository JSON files |
| Gateway TypeScript check | Pass: `npm run check` |
| Gateway no-spend smoke test | Pass: auth, readiness, budget reservation, validation; no paid dispatch |
| Dashboard JavaScript syntax | Pass: `node --check matrix.js` |
| Git whitespace check | Pass: `git diff --check` |
| Tracked secrets | No real `.env`, key, or PEM files tracked |

The smoke suite injects a fake TaskClient and deliberately fails before any real Blocks task can be sent. It tests authentication rejection, request IDs, source validation, content-type validation, idempotency-header validation, and conservative budget exhaustion without spending money.

## Remaining findings

### External release blockers

#### EXT-001 — Live Blocks deployment is not verified

**Status:** Open — requires credentials and platform access.

Run `blocks check` in every native project, register privately, verify provider runtimes, perform controlled private trigger tests, and confirm that the live billing mode matches the gateway's `billingMode: 'paid'`. Record agent versions, registry identifiers, runtime status, and test results in a release record.

#### EXT-002 — A2A invitations and permissions are not verified

**Status:** Open — requires the orchestrator machine identity.

Confirm that all required specialist invitations are accepted and that the orchestrator can call each private specialist. Test partial permission failure, timeout, cancellation, and artifact download behavior on the private network.

#### EXT-003 — Secret-manager and rotation controls are not verified

**Status:** Open — hosting/platform dependent.

Inject `BLOCKS_API_KEY`, `GATEWAY_CLIENT_KEYS`, and optional `GATEWAY_CLIENT_AGENTS` through the deployment secret manager. Do not bake secrets into images or commit them. Test rotation, revocation, expiry alerting, access review, and recovery.

#### EXT-004 — Centralized production observability is not verified

**Status:** Open — hosting/platform dependent.

Ship structured gateway logs and provider logs to a centralized system. Add alerts for readiness failures, task failure rate, latency, cancellation failures, quota saturation, A2A permission failures, and spend anomalies. The built-in gateway logs and counters are useful baseline signals, not a complete monitoring system.

#### EXT-005 — Paid canary and budget approval are not verified

**Status:** Open — requires explicit owner approval.

Run a small private paid canary only after the preceding gates pass. Define a maximum spend, test success/failure/timeout/large-artifact cases, confirm idempotent caller retries, and document rollback and incident ownership. Never use the local smoke test as a substitute for the paid canary.

### Intentional model gate

#### MODEL-001 — Forecasting remains blocked

**Status:** Intentional `FAIL`; do not remove yet.

The current panel has eight quarterly yield observations per asset, repeated provenance-labeled rows, supplied target fields, and no demonstrated independent out-of-time outcomes. Add dated history, define row selection, use chronological evaluation, compare baselines, and report uncertainty/calibration before enabling forecasting claims.

## Positive controls

- Canonical `yield_data.csv` is synchronized across deployments.
- Handlers reject undeclared, absolute, and traversal context paths.
- Evidence includes embedded `source_file`/`source_row` provenance.
- Native adapters preserve the Blocks `request` input and artifact envelope.
- Gateway caller authentication is separate from Blocks authentication.
- Paid task budgets are conservative and persisted for the single-instance topology.
- Gateway timeouts attempt remote cancellation and sessions are closed.
- A2A orchestration uses bounded parallelism, timeouts, cleanup, artifact handling, and partial-failure merging.
- Forecasting does not overclaim readiness.
- No-spend validation is available for routine CI.

## Release decision

### Conditional private pilot: allowed after external gates

The repository is ready for a controlled private pilot **only when** `blocks check`, private registration, provider connectivity, A2A permission checks, runtime secret injection, and a supervised single gateway deployment have been completed. Keep the gateway on private networking or behind an authenticated reverse proxy.

### Public or unattended paid production: NO-GO

Do not yet:

- Expose the gateway directly to the public Internet.
- Run multiple gateway replicas with only the local budget ledger.
- Publish public listings that imply live data, validated forecasts, guaranteed returns, or investment advice.
- Remove the forecasting `FAIL` gate.
- Treat local tests as proof of live Blocks readiness.

## Release gates

- [x] Gateway caller authentication and canonical request validation implemented.
- [x] Per-client rate limits and persisted single-instance task/spend budgets implemented.
- [x] Request IDs, structured logs, liveness, and readiness endpoints implemented.
- [x] Supervised non-root Docker deployment supplied.
- [x] CSV/dictionary contract reconciled and checked automatically.
- [x] No-spend gateway security and budget tests added.
- [x] Forecasting safety gate retained.
- [ ] `blocks check` passes for every native project.
- [ ] Private registration and provider connectivity verified.
- [ ] Specialist invitations are active for the orchestrator identity.
- [ ] Runtime secrets are injected through a production secret manager.
- [ ] Centralized metrics, logs, alerting, and spend monitoring are active.
- [ ] Budgeted paid canary passes with explicit owner approval.
- [ ] Public-facing data age, provenance, limitations, and non-advisory disclosures approved.

## Recommended next steps

1. Install/authenticate the Blocks CLI and run `blocks check` for every deployment project.
2. Register and test privately; verify each provider runtime and all A2A grants.
3. Deploy the gateway with the provided Docker supervision and secret manager.
4. Put the gateway behind an authenticated reverse proxy or private network.
5. Connect centralized logs/metrics and configure spend/readiness alerts.
6. Run the smallest approved paid canary and record results.
7. Expand dated data and validate forecasting separately before making any model claims.

## Audit limitations

This report is based on repository inspection and no-spend local validation. It is not a penetration test, financial-model certification, Blocks account audit, cloud configuration audit, or production SLO certification. External platform and hosting controls remain the operator's responsibility.

## References

- [Blocks documentation](https://blocks.ai/docs)
- [Blocks Quickstart](https://blocks.ai/docs/quickstart)
- [Blocks key concepts](https://blocks.ai/docs/key-concepts)
- [Blocks authentication reference](https://blocks.ai/docs/authentication)
- [`validate.md`](validate.md)
- [`setup.md`](setup.md)
- [`crypto_yield_matrix_node_gateway/README.md`](crypto_yield_matrix_node_gateway/README.md)
- [`crypto_yield_matrix_node_gateway/server.ts`](crypto_yield_matrix_node_gateway/server.ts)
- [`blocks_deploy/crypto_yield_a2a_orchestrator/handler.py`](blocks_deploy/crypto_yield_a2a_orchestrator/handler.py)
