# Production Readiness Audit and Improvement Opportunity Report

**Project:** Crypto Yield Matrix / Blocks.ai agent fleet
**Audit date:** 2026-08-07
**Audit type:** Repository, local-runtime, security-control, deterministic-packaging, deployment-topology, and no-spend validation review
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
- Deterministic source mirroring now records SHA-256 hashes for 151 files across 11 data-consuming deployments.
- Standard native adapter wrappers and deployment metadata are generated from card contracts; native `agent-card.json` files are consistency-validated, and the custom A2A adapter is preserved explicitly.
- Native Python dependencies and the Node SDK are pinned to version 1.0.11.
- Guarded trigger tooling defaults to a no-spend dry run, requires explicit paid acknowledgement, and rejects failed/canceled terminal states.
- Packaging tests exercise the root scaffold and a materialized native deployment package.
- Artifacts explicitly preserve missing numeric values as JSON `null` instead of silently converting them to zero.

Those controls make the project appropriate for local development and a supervised private pilot. They do **not** prove that the live Blocks agents are registered, reachable, paid-configured, correctly permissioned, or monitored. The gateway now defaults to an explicit loopback bind, refuses non-loopback binds unless an operator explicitly opts in, exposes a file-based emergency stop, caps artifact responses, emits release/schema/budget metadata, and has deterministic no-spend resilience coverage. The budget ledger remains a deliberate single-instance financial-control design; horizontal scaling still requires shared atomic quota accounting.

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
| Card-contract adapter check | **PASS** | 23 generated wrapper/metadata outputs plus native-card consistency validation; 0 differences |
| Deterministic mirror check | **PASS** | 151 source files across 11 deployments; 0 missing and 0 mismatched |
| Packaging tests | **PASS** | 8 standard-library no-spend tests, including root and materialized deployment behavior |
| Guarded trigger safety | **PASS** | Dry-run, acknowledgement, missing-key, and failed-terminal-state tests pass |
| Native dependency pin check | **PASS** | Python and Node Blocks SDK dependencies pinned to 1.0.11 |
| Gateway resilience suite | **PASS** | No-spend deterministic capacity saturation, timeout cleanup path, and metrics checks |
| Gateway bind/stop/response controls | **PASS** | Explicit loopback policy, kill-switch readiness, schema marker, budget headers, release ID, artifact caps |

The gateway smoke test uses a fake `TaskClient` and a placeholder key. Its successful result proves local routing and safety checks only; it is not evidence of a successful Blocks call.

### 3.2 Repository inventory

- Native deployment projects: **12** under `blocks_deploy/`.
- Data-consuming deployments synchronized: **11**.
- A2A orchestrator: intentionally data-free and excluded from data-copy checks.
- Gateway agents served: **12**.
- Gateway `package.json` and lockfile pin `@blocks-network/sdk` to **1.0.11**.
- All 12 native Python projects pin `blocks-network==1.0.11`.
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
- `/ready` checks SDK-client initialization, local budget availability, and the emergency kill switch without dispatching a task.
- `/metrics` is authenticated and no-spend.
- The default listener is loopback-only; non-loopback startup requires explicit `GATEWAY_ALLOW_PUBLIC_BIND=true`.
- A configured kill-switch file pauses new paid dispatches and makes readiness fail closed.
- Responses expose a release ID, request schema version, remaining task/spend budget headers, and bounded artifact behavior.
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
- `common.py` now exposes a `data_quality` policy: missing, blank, invalid, NaN, and infinite numeric values serialize as JSON `null`; supplied zero remains zero.

### 4.4 Remediation status since the previous audit

| Prior concern | Current status | Evidence |
|---|---|---|
| Shared-handler mirror drift | **Resolved for approved mirrors** | `sync_deployments.py --check`; 151 files, 11 deployments, 0 mismatches |
| Manual native adapter drift | **Reduced and guarded** | `generate_deployments.py`; 11 generated wrappers, 12 metadata records, native cards consistency-validated, stable card/runtime checks |
| Floating Blocks SDK versions | **Resolved for current revision** | Python `blocks-network==1.0.11`; Node `@blocks-network/sdk` `1.0.11`; CI pin check |
| Unsafe local/private trigger flow | **Resolved locally** | `trigger_guarded.py`; default dry run, explicit paid acknowledgement, non-success rejection |
| Missing scaffold/package coverage | **Resolved locally** | 8 standard-library packaging tests cover source and materialized deployment behavior |
| Silent numeric fallback to zero | **Resolved in artifacts** | `value()` preserves unavailable values; `data_quality` documents `null` semantics |
| Live Blocks/platform verification | **Open** | No CLI, registration, provider, A2A, billing, or paid-canary evidence in this environment |
| Production-scale resilience evidence | **Partially resolved locally** | Deterministic no-spend capacity/timeout suite passes; live load, restart, resource, and multi-instance budget evidence remains open |

These resolved items improve repository integrity and release repeatability; they do not establish live platform readiness.

## 5. Findings and improvement opportunities

Severity reflects risk to public unattended paid operation, not only local code quality.

### CR-001 — Live paid production state is unverified

**Status:** Open; external blocker.
**Evidence:** The `blocks` CLI is not on PATH, and no live registration, runtime, billing, trigger, or published-agent evidence was supplied. Local smoke tests and `trigger_guarded.py --dry-run` deliberately do not dispatch a task. The guarded live path explicitly requests `billing_mode="paid"`, but it has not been executed here.

**Risk:** The fleet may fail registration, use different live card versions, reject paid calls, be unavailable, or partially fail A2A despite local success.

**Required action:** Install/authenticate the official CLI in an operator-controlled environment; run `blocks check` in all 12 native projects; privately register/update cards; verify provider runtime status; run controlled private triggers; record agent names, versions, registry IDs, billing mode, runtime state, and timestamps in a release record.

### CR-002 — Public exposure depends on deployment topology, not gateway code alone

**Status:** Repository remediation complete; external edge verification remains open.
**Evidence:** `index.ts` now calls `server.listen(port, host)`, defaults `GATEWAY_HOST` to `127.0.0.1`, and refuses every non-loopback host unless `GATEWAY_ALLOW_PUBLIC_BIND=true`. Compose keeps host publication loopback-only while allowing the container to bind its private interface. The application still has no built-in TLS or reverse-proxy identity integration.

**Risk:** Public callers could reach operational endpoints or attempt billable invocation if the deployment omits a trusted authenticated edge. Authentication keys may also be exposed over an unsafe transport.

**Remaining external action:** Keep the application private behind a TLS-terminating, identity-aware reverse proxy or private network. Verify firewall rules, TLS renewal, edge-to-gateway trust, and that no unauthenticated public path exists. The no-spend smoke test now covers the loopback/non-loopback policy parser; network reachability must still be tested in the actual host environment.

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

**Status:** Repository remediation complete; fleet verification remains external.
**Evidence:** `/ready` remains no-spend and now checks SDK initialization, budget availability, and the kill switch while reporting release ID and remaining budget. It intentionally does not verify every published agent, provider runtime, A2A grant, or live task.

**Remaining external action:** Keep `/ready` no-spend and run an operator-only fleet verification job that checks registry metadata and provider health without creating paid tasks where the platform permits. Record the last successful paid canary separately from liveness/readiness; do not make readiness depend on an uncontrolled paid call.

### HI-003 — Native service supervision is not production-proven

**Status:** Open.
**Evidence:** The PowerShell process manager is suitable for local Windows operation; Docker Compose supplies basic restart supervision, but no production service manager, rolling deployment, resource limits, backup policy, or tested rollback is present.

**Required action:** Run the gateway and provider runtimes under a supported supervised platform with restart policy, CPU/memory/process limits, immutable versioned images, health-based replacement, secret injection, persistent ledger backup, and rollback. Treat the PowerShell script as development tooling, not HA supervision.

### HI-004 — Dependency upgrades require controlled release evidence

**Status:** Resolved for the current repository revision; upgrade process remains operational.
**Evidence:** The Node gateway pins `@blocks-network/sdk` to `1.0.11` in both `package.json` and `package-lock.json`; all 12 native Python projects pin `blocks-network==1.0.11`. CI checks the Python pins, and packaging metadata records the external `blocks check` requirement.

**Residual risk:** A future dependency upgrade can still change paid billing, cancellation, artifact, or task-schema behavior.

**Required action:** Treat upgrades as deliberate release changes: run no-spend checks, native `blocks check`, and an owner-approved private canary before promotion. Do not revert to floating `latest` dependencies.

### HI-005 — Live A2A permissions are unverified

**Status:** Open.
**Evidence:** The orchestrator code and mocked tests are present, but private specialist invitations, acceptance, grants, and live partial-failure behavior were not verified.

**Required action:** Verify the orchestrator machine identity has active grants for every required specialist. Run private tests for success, permission denial, timeout, cancellation, missing/large artifacts, and partial specialist failure. Capture the exact result for each specialist.

### HI-006 — Secret lifecycle is documented but not evidenced

**Status:** Open.
**Evidence:** Ignore rules and templates are correct; no production secret manager, rotation event, revocation test, expiry alert, or access review is available in the repository.

**Required action:** Inject `BLOCKS_API_KEY`, `GATEWAY_CLIENT_KEYS`, and optional allowlists at runtime. Test dual-key rotation, old-key revocation, expired-key behavior, recovery, least-privilege access, and audit logging. Never bake secrets into images or `.env` artifacts.

### ME-001 — Production-scale load, resilience, and resource-budget evidence

**Status:** Repository baseline improved; production-scale evidence remains open.
**Evidence:** `crypto_yield_matrix_node_gateway/resilience.ts` now provides a deterministic no-spend fake-provider check for capacity saturation, timeout handling, and metrics. Smoke coverage also verifies bind policy, kill-switch readiness, schema rejection, and remaining-budget headers. There is still no repeatable production-scale load test for process restart, resource limits, large live artifacts, or multi-instance accounting.

**Remaining action:** Run an approved private load/restart/resource test and keep it out of ordinary CI if it can dispatch paid work. Before a second gateway replica, deploy shared atomic quota/spend accounting.

### ME-002 — Paid canary and rollback are not evidenced

**Status:** Open; mandatory before paid unattended release.
**Repository control:** The guarded trigger now requires `--live --confirm-paid`, forces the paid SDK mode, and exits nonzero for failure, cancellation, or timeout. That safety control is locally tested; it is not a live canary.
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
- [x] Deterministic source mirrors and card-contract wrapper/metadata outputs pass local and CI checks.
- [x] SDK dependency is pinned to the tested exact version and build provenance is recorded in packaging metadata.
- [x] Deterministic adapter generation and source-to-deployment hash checks pass in CI.
- [x] Root scaffold and one materialized deployment package pass no-spend tests.
- [x] Guarded trigger requires explicit paid acknowledgement and rejects non-success terminal states.
- [x] Gateway response/schema, release, budget-header, artifact-cap, and kill-switch controls are implemented and no-spend tested.
- [x] Deterministic no-spend gateway resilience test passes for capacity saturation, timeout, and metrics.
- [ ] Production-scale load, restart, resource, and multi-instance accounting evidence passes.

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
- [x] Repository listener policy defaults to loopback and rejects non-loopback binds without explicit opt-in.
- [ ] Production listener, firewall, TLS edge, and unauthenticated reachability are verified in the target environment.
- [ ] Per-user/org authentication and agent authorization are mapped to a documented policy.
- [ ] Production secrets are injected by a secret manager and are absent from images, logs, and repository artifacts.
- [ ] Key rotation, revocation, expiry alerting, access review, and recovery are tested.
- [ ] A single gateway instance is enforced, or shared atomic quota/spend accounting is deployed before scaling.

### Reliability, operations, and finance

- [ ] Gateway and provider runtimes use supervised deployment with resource limits, health-based restart, versioned rollout, backup, and rollback.
- [ ] Centralized structured logs, metrics, dashboards, alert routing, retention, and incident ownership are active.
- [ ] Alerts cover failures, latency, cancellations, A2A grants, auth abuse, capacity, budget, and spend anomalies.
- [ ] Owner-approved paid canary completes under a hard spend ceiling and results are reconciled to Blocks billing.
- [x] Repository kill-switch file blocks new paid dispatches and fails readiness; no-spend smoke coverage exercises it.
- [ ] Production emergency stop/kill-switch procedure is tested by the accountable operator.
- [ ] Public disclosures identify data age, provenance, coverage, limitations, and non-advisory status.
- [ ] Incident runbook and release record are approved by an accountable owner.

## 8. Recommended execution order

1. Keep the pinned SDK versions, generated-adapter checks, and SHA-256 mirror checks mandatory in CI.
2. Add no-spend load/resilience tests for concurrency, artifacts, restart, and resource limits.
3. Install/authenticate the Blocks CLI in the controlled release environment.
4. Validate, privately register, and version all 12 native projects.
5. Verify provider connectivity and every A2A invitation/grant.
6. Harden deployment edge behavior: explicit private bind, TLS/auth proxy, firewall, and one-instance budget policy.
7. Configure secret manager injection, rotation, centralized logs/metrics, alerts, backups, and rollback.
8. Run private functional and failure triggers without exceeding the approved test budget.
9. Run the smallest owner-approved paid canary; reconcile task count, spend, outputs, and logs.
10. Approve public disclosures and incident ownership.
11. Promote to public/unattended paid production only after every GO checkbox is evidenced in a dated release record.

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
