# Production Readiness Audit and Improvement Opportunity Report

**Project:** Crypto Yield Matrix / Blocks.ai agent fleet
**Audit date:** 2026-08-07
**Audit type:** Repository, local-runtime, security-control, deployment-topology, and no-spend validation review
**Requested outcome:** Prepare the system for public and unattended paid production
**Current verdict:** **NO-GO for public or unattended paid production; CONDITIONAL PRIVATE-PILOT READY after external verification**

> This report does not convert unverified platform or hosting assumptions into a GO. A public paid-production GO requires live Blocks, identity, billing, network, secret-management, monitoring, and canary evidence in addition to passing repository tests.

## 1. Executive decision

The repository has materially improved production protections:

- Paid invocation requires a gateway credential separate from `BLOCKS_API_KEY`.
- Per-client agent allowlists, rolling request limits, concurrent-task limits, and UTC-day task/spend reservations are implemented.
- The budget ledger is persisted atomically for the intended single-gateway topology.
- Request IDs, structured completion/rejection logs, liveness, readiness, and protected no-spend metrics are implemented.
- The canonical data boundary is enforced: handlers accept `yield_data.csv` only, while generated asset files are clearly enrichment views.
- The data dictionary, canonical CSV mirrors, asset catalog, and 59 per-asset files are validated.
- The forecasting handler remains blocked rather than presenting unsupported predictions.
- A2A orchestration has mocked timeout, partial-failure, artifact, and cleanup coverage.

Those controls make the project appropriate for local development and a supervised private pilot. They do **not** prove that the live Blocks agents are registered, reachable, paid-configured, correctly permissioned, or monitored. The current gateway also remains a single-instance financial-control design, and its direct Node listener has no explicit host-binding configuration; the provided Compose file is localhost-bound, but another deployment could accidentally expose the process on all interfaces.

### Release decision

| Release mode | Decision | Reason |
|---|---|---|
| Local development / demonstrations | **GO** | No-spend validation passes. |
| Private, supervised pilot | **CONDITIONAL GO** | Requires live private Blocks verification, secret injection, private networking, and an approved canary. |
| Public gateway with unattended paid tasks | **NO-GO** | Live platform, identity, billing, monitoring, aggregate-budget, and canary evidence is incomplete. |
| Validated forecasting product | **NO-GO** | The intentional forecasting readiness gate remains `FAIL`. |

## 2. Audit scope and limitations

Reviewed:

- Gateway authentication, authorization, request validation, billing mode, idempotency forwarding, timeouts, cancellation, budget reservation, metrics, logging, shutdown, and Docker topology.
- Native deployment cards, provider project structure, A2A orchestrator, local handlers, data provenance, generated asset catalog, and mirror synchronization.
- Secret ignore rules, environment templates, local process management, package manifests, tests, smoke checks, and operator documentation.
- No-spend local execution and static invariants; no live paid task, registration, publishing, invitation acceptance, or production mutation was performed.

Not verified in this environment:

- A working `blocks` CLI: it is **not on PATH**.
- Blocks account, organization, registry, provider runtime connectivity, billing configuration, or live agent versions.
- Private invitation acceptance and A2A authorization for the orchestrator identity.
- Hosting firewall, reverse proxy, TLS, identity provider, secret manager, container runtime, backup, alerting, and log-retention configuration.
- Real paid latency, throughput, cancellation behavior, spend, failure rates, or artifact sizes.

## 3. Evidence collected

### 3.1 No-spend validation: PASS

The authoritative local suite completed without network calls or paid task dispatch:

| Check | Result | Evidence |
|---|---|---|
| Canonical CSV audit | **PASS** | `audit_csv.py`: 118 rows, 61 columns, 0 issues |
| Canonical unique symbols | **PASS** | 59 unique symbols |
| Asset catalog | **PASS** | 59 rows; 9 source-backed snapshots and 50 `canonical_only` rows |
| Per-asset files | **PASS** | 59 files under `csv/assets/`, filename set and row content match catalog |
| Deployment data mirrors | **PASS** | 11 data-consuming deployment copies match canonical `yield_data.csv` |
| Python AST parsing | **PASS** | Repository Python files parsed successfully |
| JSON parsing | **PASS** | Repository JSON files parsed successfully |
| Local handler smoke | **PASS** | All local agent cards/handlers returned valid artifacts |
| A2A mocked tests | **PASS** | Orchestrator partial-failure and timeout behavior tested; orchestrator remains data-free |
| Gateway TypeScript check | **PASS** | `npm run check` |
| Gateway no-spend smoke | **PASS** | Auth, readiness, protected metrics, request validation, budget behavior, 12-agent listing; no paid dispatch |
| Dashboard syntax | **PASS** | `node --check matrix.js` |
| Git whitespace | **PASS** | `git diff --check` |
| Tracked secret scan | **PASS** | No real `.env`, PEM, key, or credential file tracked by the inspected patterns |

The gateway smoke test uses a fake `TaskClient` and a placeholder key. Its successful result proves local routing and safety checks only; it is not evidence of a successful Blocks call.

### 3.2 Repository inventory

- Native deployment projects: **12** under `blocks_deploy/`.
- Data-consuming deployments synchronized: **11**.
- A2A orchestrator: intentionally data-free and excluded from data-copy checks.
- Gateway agents served: **12**.
- Gateway package lock resolves `@blocks-network/sdk` to **1.0.11**, while `package.json` declares the dependency as `latest`.
- Native agent cards provide bounded runtime settings: most specialists use concurrency 4, backlog 20, and 45-second runtime; the orchestrator uses concurrency 2, backlog 8, and 90-second runtime.

## 4. Verified controls

### 4.1 Gateway security and spend controls

Verified in `crypto_yield_matrix_node_gateway/server.ts` and `smoke.ts`:

- Separate caller bearer authentication through `GATEWAY_CLIENT_KEYS`.
- Constant-time secret comparison and rejection of client secrets equal to the Blocks API key.
- Optional per-client agent authorization through `GATEWAY_CLIENT_AGENTS`.
- JSON content-type, body-size, question-length, source-file, route, and idempotency-header validation.
- Canonical `source_file` enforcement for `yield_data.csv`.
- Per-client rolling request limit.
- Process-local concurrent paid-task cap.
- Daily task and estimated-spend reservation before SDK dispatch.
- Conservative reservation policy: uncertain, failed, or canceled requests remain reserved because their remote billing outcome is not known.
- Atomic persisted JSON ledger for the single-instance deployment.
- No application retry after an uncertain paid send.
- Best-effort remote cancellation after task or artifact timeout.
- Forwarding of `X-Idempotency-Key` to Blocks.

The configured Blocks client uses `billingMode: 'paid'`; the gateway does not expose the server-side API key in responses.

### 4.2 Operational baseline

Verified in the repository:

- `/health` is a no-spend liveness endpoint.
- `/ready` checks SDK-client initialization and local budget availability without dispatching a task.
- `/metrics` is authenticated and no-spend.
- Structured logs include request correlation and omit payloads/secrets.
- Docker runs as non-root `node` and includes a restart policy, readiness health check, and persistent budget volume.
- Compose binds the gateway to `127.0.0.1:3000` by default.
- `Restart-BlocksAgents.ps1` only terminates PIDs previously recorded by itself and is safer than broad process-name termination for local use.

### 4.3 Data integrity and user-value controls

- `yield_data.csv` remains the sole handler source.
- Embedded `source_file` and `source_row` values preserve provenance; historical labels are metadata, not alternate files.
- `asset_catalog.csv` and `csv/assets/*.csv` are generated enrichment views and label unavailable market snapshots as `canonical_only` rather than fabricating values.
- Generated fields are transparent: `yield_momentum`, `mcap_to_tvl`, `risk_score`, and `yield_premium`.
- Common artifacts include `user_value.decision_use`, `user_value.review_next`, and `user_value.do_not_infer`.
- Forecasting remains a deliberate `FAIL` until dated history, independent outcomes, chronological validation, and uncertainty reporting are available.
- Context-file access is read-only and restricted to an explicit allowlist; absolute and traversal paths are rejected.

## 5. Findings and improvement opportunities

Severity reflects risk to public unattended paid operation, not only local code quality.

### CR-001 — Live paid production state is unverified

**Status:** Open; external blocker.
**Evidence:** The `blocks` CLI is not on PATH, and no live registration, runtime, billing, trigger, or published-agent evidence was supplied. Local smoke tests deliberately do not dispatch a task.

**Risk:** The fleet may fail registration, use different live card versions, reject paid calls, be unavailable, or partially fail A2A despite local success.

**Required action:** Install/authenticate the official CLI in an operator-controlled environment; run `blocks check` in all 12 native projects; privately register/update cards; verify provider runtime status; run controlled private triggers; record agent names, versions, registry IDs, billing mode, runtime state, and timestamps in a release record.

### CR-002 — Public exposure depends on deployment topology, not gateway code alone

**Status:** Open; high risk until the edge is verified.
**Evidence:** Compose binds `127.0.0.1:3000`, but `index.ts` calls `server.listen(port)` without an explicit host and the gateway has no built-in TLS or reverse-proxy identity integration. A direct container/VM deployment can therefore expose the service more broadly than intended.

**Risk:** Public callers could reach operational endpoints or attempt billable invocation if the deployment omits a trusted authenticated edge. Authentication keys may also be exposed over an unsafe transport.

**Required action:** Make host binding explicit and keep the application private behind a TLS-terminating, identity-aware reverse proxy or private network. Document firewall rules, allowed origins if a browser client is added, TLS renewal, and an authenticated edge-to-gateway trust boundary. Add an integration check that the production listener is not publicly reachable without the edge policy.

### CR-003 — Aggregate spend protection is single-instance

**Status:** Open for horizontal scaling; acceptable only for one supervised gateway.
**Evidence:** `GATEWAY_MAX_CONCURRENT_TASKS`, rolling windows, and the JSON budget ledger are process/local-volume controls. Multiple gateway replicas would each reserve against their own state.

**Risk:** Scaling the gateway can bypass the intended task and spend ceilings and create duplicate or excessive paid work.

**Required action:** Before any second gateway replica, replace the local ledger with a shared durable atomic quota/budget service, or enforce one gateway instance at the edge and document that constraint. Add reconciliation against Blocks billing records and an emergency global kill switch.

### HI-001 — Centralized observability and alerting are not verified

**Status:** Repository baseline implemented; production control open.
**Evidence:** Local `/metrics` and JSON logs exist, but no external collector, dashboard, retention policy, alert routing, or spend monitor is present in the repository.

**Required action:** Export metrics/logs to a centralized system and alert on readiness failure, 5xx rate, p95/p99 latency, task timeout/cancellation, A2A permission errors, rate/budget/capacity saturation, authentication rejection spikes, artifact failures, and spend divergence. Redact secrets and payloads, define retention, and assign an incident owner.

### HI-002 — Readiness is configuration readiness, not fleet readiness

**Status:** Open.
**Evidence:** `/ready` initializes the shared SDK client and checks local budget; it does not verify every published agent, each provider runtime, A2A grants, or a live task.

**Required action:** Keep `/ready` no-spend, but add an operator-only fleet verification job that checks registry metadata and provider health without creating paid tasks where the platform permits. Report the last successful paid canary separately from liveness/readiness; do not make readiness depend on an uncontrolled paid call.

### HI-003 — Native service supervision is not production-proven

**Status:** Open.
**Evidence:** The PowerShell process manager is suitable for local Windows operation; Docker Compose supplies basic restart supervision, but no production service manager, rolling deployment, resource limits, backup policy, or tested rollback is present.

**Required action:** Run the gateway and provider runtimes under a supported supervised platform with restart policy, CPU/memory/process limits, immutable versioned images, health-based replacement, secret injection, persistent ledger backup, and rollback. Treat the PowerShell script as development tooling, not HA supervision.

### HI-004 — Dependency reproducibility is weakened by `latest`

**Status:** Open.
**Evidence:** `package.json` declares `@blocks-network/sdk: "latest"`, while the lockfile currently resolves 1.0.11.

**Risk:** A future clean install or lockfile refresh can change SDK behavior without an application change, especially around paid billing, cancellation, artifact APIs, or task schemas.

**Required action:** Pin the SDK to the tested exact version, use lockfile-only installs in CI/builds, review updates deliberately, and run the no-spend suite plus a private canary before upgrading.

### HI-005 — Live A2A permissions are unverified

**Status:** Open.
**Evidence:** The orchestrator code and mocked tests are present, but private specialist invitations, acceptance, grants, and live partial-failure behavior were not verified.

**Required action:** Verify the orchestrator machine identity has active grants for every required specialist. Run private tests for success, permission denial, timeout, cancellation, missing/large artifacts, and partial specialist failure. Capture the exact result for each specialist.

### HI-006 — Secret lifecycle is documented but not evidenced

**Status:** Open.
**Evidence:** Ignore rules and templates are correct; no production secret manager, rotation event, revocation test, expiry alert, or access review is available in the repository.

**Required action:** Inject `BLOCKS_API_KEY`, `GATEWAY_CLIENT_KEYS`, and optional allowlists at runtime. Test dual-key rotation, old-key revocation, expired-key behavior, recovery, least-privilege access, and audit logging. Never bake secrets into images or `.env` artifacts.

### ME-001 — No load, resilience, or resource-budget test suite

**Status:** Open.
**Evidence:** Tests cover routing and mocked logic, but there is no repeatable load test for concurrency, queue saturation, large artifacts, slow providers, process restart, or memory growth.

**Improvement:** Add a no-spend fake-provider load harness that proves 401/403/429/503 behavior, bounded memory, request correlation, ledger atomicity, graceful shutdown, and timeout cleanup. Add a separately approved private load/canary plan that never runs in ordinary CI.

### ME-002 — Paid canary and rollback are not evidenced

**Status:** Open; mandatory before paid unattended release.
**Required action:** Define an owner-approved maximum spend and one or a few test requests. Verify billing, artifact retrieval, idempotency behavior, timeout/cancel behavior, logs, metrics, ledger reservation, and rollback. Stop immediately on unexpected task count, cost, agent, or output.

### ME-003 — Data freshness and coverage limit user value

**Status:** Open as a product limitation, not a code defect.
**Evidence:** The catalog has 9 source-backed snapshots and 50 canonical-only assets; the canonical file is a historical/provenance dataset, not a live market feed.

**Improvement:** Add an explicit dataset timestamp/freshness banner to every dashboard and artifact, expose per-field coverage and source age, allow users to filter source-backed versus canonical-only assets, and add a refresh pipeline with source hashes and approval gates. Never imply real-time pricing or liquidity.

### ME-004 — Forecasting and target interpretation remain unsafe for production claims

**Status:** Intentional safety gate.
**Evidence:** Eight quarterly observations per asset, repeated provenance rows, supplied target fields, no independent outcomes, and no demonstrated walk-forward validation.

**Improvement:** Collect dated observations, define a row-selection policy, separate labels from features, use chronological train/validation/test splits, compare naive baselines, report calibration and uncertainty, and retain `FAIL` until predeclared thresholds are met.

### ME-005 — Public API product protections can be stronger

**Status:** Open improvement.
**Improvement:** Add per-organization quotas, a user-visible remaining-budget response, an administrative kill switch, an audit trail for client/agent changes, request schema versioning, maximum artifact-size policy, and clear error codes. Consider a queue only if it preserves idempotency and global spend accounting.

## 6. User-value improvement opportunities

These improvements increase usefulness while preserving evidence-first behavior:

1. **Decision-oriented report modes:** Add explicit modes for risk screen, liquidity screen, sustainability screen, methodology comparison, and portfolio scenario comparison, each with a defined output schema.
2. **Evidence drawer/export:** Let users open the exact canonical row, provenance label, catalog coverage status, formula inputs, and source snapshot file from every finding; provide JSON/CSV export with hashes.
3. **Freshness and confidence display:** Show dataset date, source-backed versus canonical-only status, missing-field counts, and confidence limitations beside—not below—the result.
4. **Scenario sensitivity:** Allow users to vary yield, inflation, drawdown, fee, lockup, and slippage assumptions and show which conclusions change. Label this as scenario analysis, not prediction.
5. **Cross-agent disagreement:** Surface conflicting specialist findings instead of flattening them into one score; show partial-failure and permission status.
6. **Cost transparency:** Show estimated task cost before dispatch, reserved daily budget after dispatch, and a safe-stop response when the budget is exhausted.
7. **Research workflow:** Add saved query IDs, reproducible request payload hashes, report version, catalog version, and “review next” checklists.
8. **Accessibility and clarity:** Keep non-advisory disclosures visible, use plain-language explanations for annualized yield and risk metrics, and ensure keyboard/mobile access to the explorer and evidence details.

## 7. Public/unattended GO release gates

The following must all be true before changing the verdict to **GO**:

### Repository and build

- [x] Canonical CSV, dictionary, catalog, per-asset files, and deployment mirrors pass automated validation.
- [x] Gateway typecheck and no-spend smoke pass.
- [x] Python handlers, JSON cards, dashboard syntax, and mocked A2A tests pass.
- [x] Forecasting `FAIL` gate and provenance restrictions remain intact.
- [ ] SDK dependency is pinned to the tested exact version and build provenance is recorded.
- [ ] No-spend load/resilience tests pass.

### Blocks platform

- [ ] `blocks check` passes in all 12 native projects using the release version.
- [ ] Private registration/update succeeds for every provider and the orchestrator.
- [ ] Registry names, versions, cards, billing mode, listing state, and expected runtime settings are recorded.
- [ ] Every provider runtime is connected and remains healthy during a controlled observation window.
- [ ] Live paid billing is confirmed for every served agent; no agent silently uses a different mode.
- [ ] Orchestrator identity has active grants for all required private specialists.
- [ ] Private triggers pass for success, invalid input, source rejection, forecast gate, timeout, cancellation, large artifact, and partial A2A failure.

### Edge, identity, and secrets

- [ ] Gateway is private by default and reachable publicly only through a TLS, authenticated, rate-limited edge.
- [ ] Direct listener host binding and firewall behavior are verified; no unauthenticated public path exists.
- [ ] Per-user/org authentication and agent authorization are mapped to a documented policy.
- [ ] Production secrets are injected by a secret manager and are absent from images, logs, and repository artifacts.
- [ ] Key rotation, revocation, expiry alerting, access review, and recovery are tested.
- [ ] A single gateway instance is enforced, or shared atomic quota/spend accounting is deployed before scaling.

### Reliability, operations, and finance

- [ ] Gateway and provider runtimes use supervised deployment with resource limits, health-based restart, versioned rollout, backup, and rollback.
- [ ] Centralized structured logs, metrics, dashboards, alert routing, retention, and incident ownership are active.
- [ ] Alerts cover failures, latency, cancellations, A2A grants, auth abuse, capacity, budget, and spend anomalies.
- [ ] Owner-approved paid canary completes under a hard spend ceiling and results are reconciled to Blocks billing.
- [ ] Emergency stop/kill-switch procedure is tested.
- [ ] Public disclosures identify data age, provenance, coverage, limitations, and non-advisory status.
- [ ] Incident runbook and release record are approved by an accountable owner.

## 8. Recommended execution order

1. Pin the SDK dependency and add no-spend load/resilience tests.
2. Install/authenticate the Blocks CLI in the controlled release environment.
3. Validate, privately register, and version all 12 native projects.
4. Verify provider connectivity and every A2A invitation/grant.
5. Harden deployment edge behavior: explicit private bind, TLS/auth proxy, firewall, and one-instance budget policy.
6. Configure secret manager injection, rotation, centralized logs/metrics, alerts, backups, and rollback.
7. Run private functional and failure triggers without exceeding the approved test budget.
8. Run the smallest owner-approved paid canary; reconcile task count, spend, outputs, and logs.
9. Approve public disclosures and incident ownership.
10. Promote to public/unattended paid production only after every GO checkbox is evidenced in a dated release record.

## 9. Release-record template

Record this outside the source tree or in an approved protected operations system:

```text
Release version:
Commit/image digest:
Audit date:
Blocks organization:
Provider registry IDs and versions:
Billing mode and listed price per agent:
Gateway image digest and SDK version:
Gateway host/edge:
Secret-manager reference and rotation date:
A2A grants verified for:
No-spend suite result:
Private trigger result:
Paid canary task IDs:
Paid canary maximum approved spend:
Actual task count / actual spend:
Rollback tested:
Monitoring dashboard / alert owner:
Incident owner:
GO approver:
Next review/expiry date:
```

## 10. Audit limitations

This is not a penetration test, financial-model certification, live Blocks account audit, cloud configuration audit, or production SLO certification. The repository can demonstrate local behavior and defensive intent; only the operator-controlled release environment can prove platform registration, identity, billing, network, secret, monitoring, and live paid behavior.

## References

- [Blocks documentation](https://blocks.ai/docs)
- [Blocks Quickstart](https://blocks.ai/docs/quickstart)
- [Blocks key concepts](https://blocks.ai/docs/key-concepts)
- [Blocks authentication reference](https://blocks.ai/docs/authentication)
- [`validate.md`](validate.md)
- [`setup.md`](setup.md)
- [`crypto_yield_matrix_node_gateway/server.ts`](crypto_yield_matrix_node_gateway/server.ts)
- [`crypto_yield_matrix_node_gateway/docker-compose.yml`](crypto_yield_matrix_node_gateway/docker-compose.yml)
- [`crypto_yield_matrix_node_gateway/Dockerfile`](crypto_yield_matrix_node_gateway/Dockerfile)
- [`blocks_deploy/crypto_yield_a2a_orchestrator/handler.py`](blocks_deploy/crypto_yield_a2a_orchestrator/handler.py)
- [`audit_csv.py`](audit_csv.py)
- [`build_asset_catalog.py`](build_asset_catalog.py)
