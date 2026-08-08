# Production Readiness Audit

**Project:** Crypto Yield Matrix / Blocks.ai agent fleet
**Audit date:** 2026-08-07
**Update:** Synchronized-state post-remediation audit
**Verdict:** **CONDITIONAL PRIVATE PILOT — NO-GO for public or unattended paid production**
**Repository state:** The current working tree contains the documented implementation, mirror-synchronization, and audit updates; no untracked secrets or alternate datasets were introduced. No paid Blocks task was dispatched during this update.

## Executive summary

The repository-controlled blockers identified in the original audit have been addressed in code and documentation. The Node gateway now requires separate caller authentication, supports per-client agent allowlists, enforces rate and daily paid-task budgets, persists the single-instance budget ledger, validates the canonical data source, emits request-correlated structured logs, and provides no-spend health/readiness endpoints. The gateway remains compatible with the Blocks consumer `TaskClient`, paid `billingMode`, forwarded idempotency keys, native provider cards, and server-side `BLOCKS_API_KEY` handling.

The canonical data contract is now explicit: `yield_data.csv` contains 118 rows, 59 unique symbols, 61 columns, 59 analytical columns, and two provenance columns. The file has no alternate CSV files beside it, but its embedded `source_file` provenance field intentionally retains two historical labels (`yield_data.csv` and `yield_data1.csv`); those labels are evidence metadata, not files to load. The dictionary distinguishes current CSV fields from planned/derived fields, and `audit_csv.py` checks that every CSV field is documented. Stale multi-source setup instructions were removed, deployment dictionary copies were synchronized, and the forecasting safety gate remains intact.

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
- Added an authenticated no-spend `/metrics` endpoint with request, status, authentication, invoke-lifecycle, and separated rate-limit, budget, and capacity rejection counters; the smoke test verifies protected access and expected outcomes.

The budget is intentionally conservative: a task reservation remains counted even if a remote result is uncertain, failed, or canceled. This prevents ambiguous network outcomes from creating uncontrolled spend. The persisted ledger is single-instance protection, not a distributed quota service; the Compose deployment mounts durable storage at `GATEWAY_BUDGET_STATE_FILE`. Do not horizontally scale gateways without replacing it with shared durable accounting.

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
- Removed stale instructions about loading a second independent dataset.
- Kept row-level provenance in research evidence so duplicate symbols remain explainable.
- Synchronized the canonical CSV, dictionary, validation report, and shared handler scaffold across all 11 data-consuming deployments.
- Kept the A2A orchestrator intentionally data-free; it receives provenance in requests and delegates to the specialist fleet.
- Preserved explicit uncertainty and non-advisory language.
- Added a consistent `user_value` contract to local research artifacts: how to use the evidence, what to review next, and what not to infer.
- Added local smoke assertions for the user-value artifact contract.
- Kept forecasting blocked until dated history and out-of-time validation exist.

## Evidence and no-spend validation

The following checks pass after remediation and the latest user-value hardening update:

| Check | Result |
|---|---|
| Canonical CSV audit | Pass: 118 rows, 61 columns, 0 issues |
| Dictionary field coverage | Pass through `audit_csv.py` |
| Deployment CSV mirrors | Pass: 11 copies byte-identical to root |
| Deployment dictionary mirrors | Pass: 11 copies byte-identical to root |
| Python syntax/AST validation | Pass for repository Python files |
| A2A orchestrator mocked tests | Pass; orchestrator remains data-free |
| JSON parsing | Pass for repository JSON files |
| Shared scaffold synchronization | Pass across 11 data-consuming deployments |
| Gateway TypeScript check | Pass: `npm run check` |
| Gateway no-spend smoke test | Pass: auth, readiness, metrics, budget reservation, validation; no paid dispatch |
| Research artifact contract | Pass: local smoke validates `user_value` guidance and provenance fields |
| Dashboard JavaScript syntax | Pass: `node --check matrix.js` |
| Git whitespace check | Pass: `git diff --check` |
| Tracked secrets | No real `.env`, key, or PEM files tracked |

The smoke suite injects a fake TaskClient and deliberately fails before any real Blocks task can be sent. It tests authentication rejection, protected metrics access, request IDs, source validation, content-type validation, idempotency-header validation, readiness behavior, and conservative budget exhaustion without spending money. Metrics distinguish rate-limit, daily-budget, and capacity rejection so alerts do not mistake client throttling for spend exhaustion. The repository-level synchronization check separately verifies that all 11 data-consuming deployments match the canonical CSV, dictionary, validation report, and shared handler scaffold; the A2A orchestrator is excluded from data-copy checks by design.

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

**Status:** Repository baseline implemented; external operational gate remains open.

The gateway now exposes authenticated no-spend `/metrics` counters for request totals, status codes, auth rejection, accepted/completed/failed invokes, and separately classified rate-limit, daily-budget, and capacity rejection, in addition to request-correlated structured logs. The local smoke test verifies protected access and counters without dispatching a task. Ship these metrics and logs to a centralized system and add alerts for readiness failures, task failure rate, latency, cancellation failures, quota saturation, A2A permission failures, and spend anomalies before production. Keep the endpoint on a trusted operational network even with bearer authentication.

#### EXT-005 — Paid canary and budget approval are not verified

**Status:** Open — requires explicit owner approval.

Run a small private paid canary only after the preceding gates pass. Define a maximum spend, test success/failure/timeout/large-artifact cases, confirm idempotent caller retries, and document rollback and incident ownership. Never use the local smoke test as a substitute for the paid canary.

#### VALUE-001 — Research artifacts previously lacked consistent interpretation guidance

**Status:** Remediated in repository; verify in native adapters.

Every local specialist artifact now includes `user_value.decision_use`, `user_value.review_next`, and `user_value.do_not_infer`. This makes the output more useful to a researcher while preserving the non-advisory boundary. Native Blocks adapters delegate to these handlers, and the local smoke harness asserts the contract; a live private trigger is still required to verify the serialized artifact end to end.

### Data contract clarification

#### DATA-001 — Embedded provenance labels are metadata, not alternate datasets

**Status:** Controlled and documented.

The canonical file has 118 rows and retains two embedded provenance labels, including the historical label `yield_data1.csv`. No `yield_data1.csv` or `consolidated_yield_data.csv` file exists in the repository or deployment projects, and handlers accept only the canonical `yield_data.csv` path. Repeated symbols must remain traceable through `source_file` and `source_row`; they must not be treated as independent time observations without a documented selection policy.

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
- [x] Request IDs, structured logs, liveness, readiness, and protected no-spend metrics endpoints implemented.
- [x] Supervised non-root Docker deployment supplied.
- [x] CSV/dictionary contract reconciled and checked automatically.
- [x] Eleven data-consuming deployment mirrors synchronized; A2A orchestrator remains data-free by design.
- [x] No-spend gateway security and budget tests added.
- [x] Forecasting safety gate retained.
- [ ] `blocks check` passes for every native project.
- [ ] Private registration and provider connectivity verified.
- [ ] Specialist invitations are active for the orchestrator identity.
- [ ] Runtime secrets are injected through a production secret manager.
- [ ] Centralized metrics, logs, alerting, and spend monitoring are active (protected repository baseline metrics now available).
- [ ] Budgeted paid canary passes with explicit owner approval.
- [ ] Public-facing data age, provenance, limitations, and non-advisory disclosures approved.

## Recommended next steps

1. Install/authenticate the Blocks CLI and run `blocks check` for all 12 native projects, including the data-free A2A orchestrator.
2. Register and test privately; verify each provider runtime and all A2A grants.
3. Deploy the gateway with the provided Docker supervision and secret manager.
4. Put the gateway behind an authenticated reverse proxy or private network.
5. Ship `/metrics` and structured logs to centralized monitoring; configure spend/readiness alerts.
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
