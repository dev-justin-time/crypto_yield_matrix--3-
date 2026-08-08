# Production Readiness Audit

**Project:** Crypto Yield Matrix / Blocks.ai agent fleet
**Audit date:** 2026-08-07
**Audit type:** Read-only repository and local-runtime review
**Verdict:** **NO-GO for public or unattended paid production**

## Executive summary

The repository is internally consistent and its local validation suite passes, but it is not yet safe to expose as a production service. The most serious blocker is the Node gateway: its paid invocation endpoint has no application-level authentication or authorization. If the process is reachable from an untrusted network, any caller could submit billable Blocks tasks.

The project also has deployment-dependent gaps that cannot be proven from local tests alone: native Blocks card validation, registration, provider connectivity, private-agent invitations, A2A authorization, paid billing configuration, and real trigger behavior. Forecasting is intentionally blocked by a readiness gate because the dataset has only eight quarterly observations per asset and no demonstrated out-of-time model validation.

The current repository is appropriate for local development, offline research prototyping, private pre-registration testing, and demonstrations behind a trusted local boundary. It is not ready for a public gateway, unattended paid workloads, customer-facing financial research, or validated forecasting claims.

## Audit scope

Reviewed:

- Repository structure, Git state, manifests, deployment cards, and native provider projects.
- Local Python handlers, provenance rules, data validation, and A2A orchestration.
- Node gateway routing, request validation, billing configuration, concurrency, timeouts, cancellation, and shutdown behavior.
- Secret handling, ignored files, local process management, logs, tests, and operational documentation.
- Safe local validation only; no paid Blocks task, registration, publishing, or production mutation was performed.

Not verified:

- Live Blocks account, organization, API key, registry state, or billing account.
- `blocks check`, `blocks register`, `blocks run`, `blocks publish`, or live trigger execution.
- Actual private invitation acceptance and A2A permissions.
- External network exposure, reverse-proxy configuration, firewall rules, hosting platform, or runtime secrets.
- Production latency, throughput, spend, failure rates, or resource usage.

## Evidence and local validation

The following checks passed during the audit:

| Check | Result |
|---|---|
| Git status | Clean working tree on `main` |
| Python compilation | Pass for `blocks_agents` and `blocks_deploy` |
| A2A orchestrator mocked tests | Pass |
| JSON parsing | 159 JSON files parsed successfully |
| Canonical CSV mirrors | Pass; deployment copies match the root file |
| Dictionary mirrors | Pass; deployment copies match the root file |
| Gateway TypeScript check | Pass: `npm run check` |
| Gateway no-spend smoke test | Pass: `npm run smoke` |
| Dashboard JavaScript syntax | Pass: `node --check matrix.js` |
| Git whitespace check | Pass: `git diff --check` |
| Tracked secret candidates | No real `.env`, key, or PEM files tracked; `.env.example` is a blank template |

The gateway smoke test intentionally uses a placeholder key and does not dispatch a paid task.

## Findings

### Critical findings

#### CR-001 — Unauthenticated paid invocation endpoint

**Status:** Open
**Evidence:** `crypto_yield_matrix_node_gateway/server.ts` exposes `POST /agents/:name/invoke` without checking an end-user credential. `BILLING_MODE` is hardcoded to `paid`, and the gateway documentation states that tasks cost approximately `$0.10/task`.

The server validates JSON shape, request size, agent name, question presence, concurrency, and idempotency-header length, but it does not authenticate the caller or authorize access to a specific agent. The Blocks API key is protected server-side, but that alone does not protect the gateway from abuse.

**Risk:** Any reachable caller may consume the Blocks account balance, submit unauthorized research requests, or create an availability incident.

**Required remediation:**

1. Add application authentication before the invocation route, preferably through a trusted identity-aware reverse proxy or a service-level JWT/API-key layer.
2. Add authorization policies for users, organizations, and agent access.
3. Add per-principal rate limits, quotas, and a hard spend budget.
4. Keep the gateway private by default and bind it only to a private interface unless the authenticated edge is guaranteed.
5. Add tests proving unauthenticated requests are rejected and authorized requests are charged only within policy.

#### CR-002 — Production deployment and live Blocks state are unverified

**Status:** Open
**Evidence:** `setup.md` explicitly states that the local scaffold and cards require native Blocks validation and that this audit environment could not verify the `blocks` CLI. Local tests do not establish that the live registry, provider runtimes, billing mode, or permissions are correct.

**Risk:** A deployment may fail at registration, remain unreachable, reject paid calls, or partially execute the A2A fleet despite passing local tests.

**Required remediation:**

- Run `blocks check` in every native deployment project.
- Register privately and verify each provider runtime remains connected.
- Run controlled private trigger tests with valid credentials.
- Confirm the live billing mode matches the gateway's `billingMode: 'paid'` setting.
- Verify all required specialist invitations are accepted by the orchestrator identity.
- Record the registry identifiers, versions, billing settings, and test results in a release record.

### High findings

#### HI-001 — Local PowerShell process manager is not a production supervisor

**Status:** Open
**Evidence:** `Restart-BlocksAgents.ps1` manages local PIDs with `.blocks-agent-state.json`, `taskkill`, and files under `blocks-agent-logs/`.

**Risk:** The script does not provide durable service supervision, health-based restarts, rolling deployment, resource isolation, centralized logs, alerting, or reliable multi-instance coordination. A stale local state file or host failure can leave runtimes unavailable.

**Required remediation:** Deploy provider runtimes and the gateway under a real service manager or container platform with restart policy, health checks, resource limits, secret injection, and controlled rollout/rollback.

#### HI-002 — Insufficient production observability

**Status:** Open
**Evidence:** The gateway provides `/health`, process uptime, client state, and in-flight counts. Runtime output is otherwise written to local console or redirected text logs.

**Risk:** Operators cannot reliably detect elevated latency, task failures, cancellation failures, A2A permission failures, quota exhaustion, abnormal spend, or data/version drift.

**Required remediation:** Add structured logs with request/task correlation IDs, metrics for request count/status/latency, provider and A2A outcomes, cancellation results, queue saturation, and estimated spend. Add dashboards, alerts, retention rules, and an operational runbook. Separate liveness from readiness; readiness should verify required external dependencies without creating a paid task.

#### HI-003 — Forecasting and model claims are not production-ready

**Status:** Intentional safety gate; Open for any forecasting release
**Evidence:** `blocks_agents/handlers/quant_forecasting_expert.py` returns `FAIL` until source identity, additional dated history, leakage-controlled walk-forward evaluation, and independent outcomes are available. The model validation handler also rejects insufficient history and invalid temporal splits.

**Risk:** Removing the gate prematurely could turn supplied target fields into unsupported forecasts or investment claims.

**Required remediation:** Add dated observations, define independent future outcomes, document a row-selection policy for repeated provenance rows, use chronological train/validation/test splits, compare simple baselines, report uncertainty and calibration, and preserve the `FAIL` gate until out-of-time results meet an explicitly documented threshold.

#### HI-004 — Data dictionary and dataset contract require reconciliation

**Status:** Open
**Evidence:** The canonical CSV contains 118 rows and 61 columns. The v2 dictionary describes 59 assets and 118 features and contains section counts that do not consistently match the listed fields.

**Risk:** Consumers may infer the wrong schema, omit fields, or train against a contract that does not match the actual CSV.

**Required remediation:** Generate or manually reconcile the dictionary against the exact CSV header. State separately: row count, unique-symbol count, column count, feature count, provenance columns, and target columns. Correct every section count and add a schema validation check that fails when the dictionary and CSV diverge.

### Medium findings

#### ME-001 — Automated test coverage is narrow

Only the A2A merge logic has a dedicated test file. Missing automated coverage includes handler contracts, malformed requests, traversal attempts, invalid symbols/categories, provenance-row selection, artifact download failures, gateway authentication, concurrency saturation, idempotency behavior, timeout cancellation, and shutdown behavior.

Add unit and integration tests for each risk boundary. Keep paid integration tests opt-in and explicitly marked so normal CI never spends money.

#### ME-002 — Documentation contains deployment drift

`setup.md` contains stale wording from the previous multi-source dataset, including duplicated filename references and old instructions describing conflicting source files. This can mislead operators even though the canonical CSV audit has been corrected.

Update the setup guide to describe only the current canonical dataset and clearly separate embedded provenance labels from independent source files. Add a documentation consistency check to CI.

#### ME-003 — Gateway billing safety is process-local

The gateway limits in-flight tasks with `GATEWAY_MAX_CONCURRENT_TASKS`, but the limit is per process. Multiple gateway instances can exceed the intended aggregate budget, and the Blocks provider backlog remains authoritative.

Use a centralized quota or budget service, or enforce concurrency and spend at the edge/provider level. Treat the current process-local limit as a protective best effort, not a financial control.

#### ME-004 — Secret lifecycle controls are not operationalized

The repository correctly ignores `.env` and key files and does not track a real credential. However, production rotation, revocation, expiry alerts, access review, and secret-manager injection are documented recommendations rather than verified controls.

Inject secrets at runtime through the hosting platform, rotate keys before expiry, restrict service identity access, and test revocation/recovery procedures.

## Positive controls already present

- Canonical `yield_data.csv` is synchronized across deployments and retains row-level `source_file`/`source_row` provenance.
- Handlers restrict context-file access through an explicit allowlist and reject absolute or traversal paths.
- Local handlers return a common artifact envelope with assumptions, limitations, and provenance.
- Forecasting remains blocked rather than presenting unsupported predictions.
- The gateway caps request bodies, validates required input, rejects unknown agents, limits in-flight paid tasks, forwards idempotency keys, and avoids blind application retries.
- Gateway task timeouts attempt remote cancellation and close sessions.
- A2A orchestration uses bounded parallelism, specialist timeouts, late-send cleanup, artifact handling, and partial-failure merging.
- API credentials are not exposed through the gateway response and no real secret is tracked in Git.
- The project documentation warns against public publishing before private validation and against treating research output as financial advice.

## Release decision

### Current decision: NO-GO

Do not:

- Expose the Node gateway to the public Internet.
- Enable unattended paid operation.
- Publish a public listing that implies live data, validated forecasts, guaranteed returns, or investment advice.
- Remove the forecasting `FAIL` gate.
- Treat local smoke tests as proof of live Blocks readiness.

### Acceptable current uses

- Local development and demonstrations.
- Offline handler and schema validation.
- Private pre-registration testing.
- Research triage and decision-support prototyping behind a trusted boundary.

## Production release gates

A release can move from **NO-GO** to **conditional private pilot** only after all of the following are complete:

- [ ] Gateway authentication and authorization implemented and tested.
- [ ] Per-user quotas, rate limiting, and aggregate spend controls implemented.
- [ ] Gateway and providers deployed under a supervised production service.
- [ ] Runtime secrets injected by a secret manager; rotation and revocation tested.
- [ ] Structured logs, metrics, dashboards, alerts, and correlation IDs available.
- [ ] CSV and dictionary schema reconciled and checked automatically.
- [ ] `blocks check` passes for every native project.
- [ ] Private registration and provider connectivity verified.
- [ ] Specialist invitations are active for the orchestrator identity.
- [ ] Controlled private triggers pass for success, failure, timeout, invalid input, and large artifacts.
- [ ] Gateway integration tests pass without paid calls in normal CI.
- [ ] Paid canary test plan, budget, rollback, and incident owner approved.
- [ ] Public-facing descriptions disclose data age, provenance, limitations, and non-advisory status.

A public or paid production release additionally requires measured load-test evidence, a documented spend ceiling, incident response procedures, and explicit review of the live Blocks billing/listing configuration.

## Recommended remediation order

1. Lock the gateway to private networking and add authentication/authorization.
2. Add quotas, rate limits, aggregate spend protection, and audit logging.
3. Reconcile the data dictionary and remove stale deployment documentation.
4. Add missing unit/integration/security tests.
5. Deploy under a supervised service with centralized observability.
6. Validate every native project privately with the Blocks CLI and controlled triggers.
7. Verify A2A permissions and partial-failure behavior on the live network.
8. Expand the dataset and complete time-aware model validation before enabling forecasting claims.
9. Conduct a private, budgeted canary before considering public or paid expansion.

## Audit limitations

This report is based on repository inspection and no-spend local validation. It is not a penetration test, financial-model validation, Blocks account audit, cloud configuration audit, or certification. The final production decision must include the hosting, identity, network, secret-management, Blocks organization, and billing controls that are external to this repository.

## References

- [Blocks documentation](https://blocks.ai/docs)
- [Blocks Quickstart](https://blocks.ai/docs/quickstart)
- [Blocks key concepts](https://blocks.ai/docs/key-concepts)
- [Blocks authentication reference](https://blocks.ai/docs/authentication)
- [`validate.md`](validate.md)
- [`setup.md`](setup.md)
- [`crypto_yield_matrix_node_gateway/server.ts`](crypto_yield_matrix_node_gateway/server.ts)
- [`blocks_deploy/crypto_yield_a2a_orchestrator/handler.py`](blocks_deploy/crypto_yield_a2a_orchestrator/handler.py)
