# Behavioral Equivalence Proof and Dependency Audit

**Project:** Crypto Yield Matrix / Blocks.ai agent fleet  
**Report:** `beproof.md`  
**Audit date:** 2026-08-07  
**Audit mode:** Read-only repository inspection plus no-spend local validation  
**Scope:** Root local handlers, native deployment adapters, generated data artifacts, live-data overlay, Node gateway, and runtime dependencies

## 1. Executive conclusion

### Behavioral-equivalence verdict: **PARTIAL / NOT PROVEN AS A WHOLE**

The repository has strong equivalence evidence for the specialized local handlers and generated canonical-data artifacts, but the entire system does not meet a strict behavioral-equivalence proof standard.

What is proven locally:

- The 11 data-consuming deployment copies contain byte-identical specialized handler implementations for the 11 indexed agents.
- The canonical CSV, generated asset catalog, quote exports, and deployment CSV mirrors pass the existing integrity audit.
- The local handler smoke test, A2A mocked test, live-overlay tests, Python parsing, JavaScript syntax check, and Node gateway no-spend checks pass.
- Native deployment wrappers delegate to the corresponding local handler logic rather than reimplementing it.

What is not proven:

- Root `blocks_agents/handlers/common.py` is **not byte-identical** to the common-handler copy in the 11 deployment projects. The deployed copy is stricter for degraded/stale live-data handling and more defensive for malformed snapshot sections. This is a real behavioral divergence at a shared dependency boundary.
- Live Blocks registration, provider connectivity, private invitations, billing configuration, A2A authorization, and paid trigger behavior were not executed.
- The 24/7 live worker was not run against live providers in this audit. No current provider response, rate-limit header, or RPC behavior is certified here.
- The live overlay is not automatically delivered to deployed paid runtimes in the supplied container configuration; container mirroring is disabled by default unless an explicit shared-volume/distribution design is provided.
- Formal semantic equivalence across all inputs, exceptions, timing, filesystem states, network failures, and SDK versions has not been established.

**Release interpretation:** The local repository is suitable for continued development and controlled private testing. This report does not establish public/unattended paid-production equivalence or a production GO decision.

## 2. Proof claims and standard

This report uses a bounded, operational definition of behavioral equivalence:

> Two implementations are behaviorally equivalent for a declared surface when they accept the same relevant inputs, use the same source policy, produce the same normalized artifact contract, and pass the same defined validation cases, subject to the same environment assumptions.

This is not a mathematical proof of program equivalence. It is a reproducible engineering proof obligation with three levels:

- **EQUIVALENT:** byte-identical source or generated content, or a verified comparison with no relevant behavioral difference in the declared surface.
- **PARTIAL:** important behavior matches, but a shared dependency, environment, external service, or untested branch prevents a complete claim.
- **NOT PROVEN:** the required evidence was not run or cannot be established from the repository.

The proof excludes claims about:

- financial performance, investment suitability, or forecast validity;
- live provider accuracy or uptime;
- Blocks platform behavior not exercised by local tests;
- arbitrary future edits to generated files or deployment environments.

## 3. Equivalence surfaces

### 3.1 Local specialized handlers vs. deployment copies

**Result: EQUIVALENT for the specialized handler source files.**

Read-only SHA-256 inventory compared each root file under `blocks_agents/handlers/` against the same path in all 11 non-orchestrator deployment projects:

| Surface | Result |
|---|---:|
| Deployment projects compared | 11 |
| Root handler Python files inspected | 14 |
| Specialized handlers byte-identical in every deployment | 11 of 11 |
| `__init__.py` byte-identical | 11 of 11 |
| `__main__.py` byte-identical | 11 of 11 |
| `common.py` byte-identical | 0 of 11 |

The specialized handlers that matched across all 11 deployments were:

- `crypto_research_communications_agent.py`
- `crypto_risk_analyst.py`
- `data_provenance_auditor.py`
- `defi_liquidity_analyst.py`
- `feature_engineering_expert.py`
- `matrix_research_insights_agent.py`
- `model_validation_guardian.py`
- `portfolio_scenario_expert.py`
- `quant_forecasting_expert.py`
- `tokenomics_sustainability_expert.py`
- `yield_methodology_expert.py`

The specialized source equality is strong evidence because these handlers import shared functions and construct the same common artifact envelope. It is not sufficient for whole-agent equivalence while their shared `common.py` differs.

### 3.2 Root common handler vs. deployment common handler

**Result: NOT EQUIVALENT; divergence is documented and safety-relevant.**

The current root `blocks_agents/handlers/common.py` is newer than the synchronized deployment copies. An exact unified diff against `blocks_deploy/crypto_risk_analyst/blocks_agents/handlers/common.py` found 42 changed diff lines; the same deployment hash group was present across all 11 data-consuming projects.

The root version has the stricter live-data behavior:

- `usable` live data requires `data_status == "live_overlay_only"`;
- retained observations with `observation_status == "retained_from_previous_cycle"` are not usable;
- the market payload is returned only when the stricter `usable` predicate passes;
- malformed `defi`, `blockchain`, and `freshness` sections receive defensive type checks.

The deployment copies use the older behavior: freshness and timestamp checks can mark an observation usable without the root version's explicit degraded-status and retained-observation exclusions, and their nested-section handling is less defensive. Therefore, if a deployment runtime reads a live snapshot, it may expose a recently retained, degraded, or malformed value differently from the root local handler.

**Required remediation before claiming fleet equivalence:** synchronize the current root `common.py` into all 11 data-consuming deployments, then rerun the hash comparison, handler smoke suite, native project checks, and deployment artifact tests.

This report intentionally records the failure instead of treating the specialized-handler matches as proof of the full handler fleet.

### 3.3 Native Blocks wrappers vs. local handlers

**Result: PARTIAL equivalence.**

The deployment wrappers such as `blocks_deploy/crypto_risk_analyst/handler.py` import and delegate to `blocks_agents.handlers.crypto_risk_analyst.handler`. This minimizes duplicate business logic and supports equivalence of the delegated computation.

The wrapper adds an external SDK boundary:

- native `blocks_network` task and context types;
- artifact transport and runtime process behavior;
- Blocks card and registry configuration;
- environment-provided credentials and permissions.

The local smoke test proves the delegated local result envelope. It does not prove that every native SDK task shape, progress callback, artifact-size path, exception, or live runtime state behaves identically.

### 3.4 Canonical CSV and generated artifacts

**Result: EQUIVALENT for the declared generated-artifact contract.**

`audit_csv.py` passed with:

- 118 canonical rows;
- 61 canonical columns;
- 11 deployment copies checked;
- 59 unique symbols;
- 59 generated catalog rows and per-asset files;
- 59 normalized quote exports;
- deployment quote mirrors passing;
- aggregate formula checks passing;
- dictionary field coverage passing;
- 0 validation issues.

The generator `build_asset_catalog.py` preserves `yield_data.csv` as the only canonical handler source and creates derived catalog/quote views. Unavailable quote values remain blank instead of being converted into fabricated zeroes.

This proves file-level contract consistency for the checked outputs. It does not prove source-data correctness, historical truth, or live freshness.

### 3.5 Live overlay, worker, dashboard, and handlers

**Result: PARTIAL / NOT PROVEN end-to-end.**

The live layer is intentionally separate from historical yield evidence:

- `live_data.py` collects provider observations into a JSON overlay;
- `live_worker.py` writes atomic snapshots and status records;
- `matrix.js` displays freshness and per-card live status;
- `common.py` reads the snapshot without making network calls from a paid task;
- stale, retained, degraded, or unavailable observations are not considered usable by the current root handler.

The local proof covers injected provider payload parsing, URL safety validation, snapshot freshness, and partial-cycle retention. It does not prove:

- actual provider response schemas at audit time;
- provider terms or limits remain unchanged;
- external network failure modes beyond the injected cases;
- live snapshot delivery into every hosted agent runtime;
- process supervision, alert delivery, or recovery after host/container failure.

The current default container configuration sets `LIVE_WORKER_MIRROR_DEPLOYMENTS=0`. That is safer than claiming unavailable propagation, but it means a separate shared-volume or distribution mechanism is required before deployed paid agents can consume the overlay.

### 3.6 Node gateway vs. direct Blocks client behavior

**Result: PARTIAL.**

The gateway adds intentional policy behavior around the shared paid `TaskClient`:

- separate caller authentication;
- client-to-agent authorization;
- body and question validation;
- in-flight capacity limits;
- per-client rate limits;
- UTC-day task/spend reservations;
- idempotency-key forwarding;
- timeout cancellation attempts;
- protected metrics;
- no-spend fake-client tests.

The gateway smoke test passed routing and safety behavior without dispatching a paid task. It does not prove equivalence to direct Blocks calls, live billing, remote cancellation, agent terminal states, artifact downloads, or idempotency behavior on the live platform.

## 4. Behavioral evidence executed

The following no-spend checks passed during this report preparation:

| Check | Result | Meaning |
|---|---|---|
| `python audit_csv.py` | PASS; 0 issues | Canonical/generated data contract and mirrors pass |
| `python run_live_tests.py` | PASS | Injected live collector, URL safety, merge, and freshness cases pass |
| `python -m blocks_agents.handlers` | PASS | All indexed local handlers return valid common artifacts |
| `python blocks_deploy/crypto_yield_a2a_orchestrator/test_handler.py` | PASS | Mocked A2A merge/timeout behavior passes |
| Python AST parse | PASS; 223 files checked | Repository Python syntax parses outside ignored environments |
| `node --check matrix.js` | PASS | Dashboard JavaScript syntax parses |
| `cd crypto_yield_matrix_node_gateway && npm run check` | PASS | Gateway TypeScript type-check passes |
| `cd crypto_yield_matrix_node_gateway && npm run smoke` | PASS | Gateway auth/readiness/budget/routing smoke passes without paid dispatch |
| `git diff --check` | PASS | No whitespace errors reported |

These results establish local behavior only. They do not replace live Blocks validation or a paid canary.

## 5. Dependency audit

### 5.1 Direct declared dependencies

#### Native Python deployment projects

There are 12 `blocks_deploy/*/pyproject.toml` files, including the A2A orchestrator. They declare:

- Python `>=3.12`;
- the `blocks-network` dependency;
- setuptools-based package metadata.

The local root handler scaffold uses Python standard-library modules and does not declare a root `requirements.txt`. Its runtime dependencies are repository files, Python, and the local loader.

#### Node gateway

`crypto_yield_matrix_node_gateway/package.json` declares:

| Type | Package | Declared range | Lockfile version |
|---|---|---:|---:|
| runtime | `@blocks-network/sdk` | `latest` | 1.0.11 |
| runtime | `dotenv` | `^16.4.5` | 16.6.1 |
| development | `@types/node` | `^22.0.0` | 22.20.1 |
| development | `tsx` | `^4.19.2` | 4.23.10 |
| development | `typescript` | `^5.4.5` | 5.9.3 |

**Dependency finding:** `@blocks-network/sdk` is declared as `latest` while the lockfile resolves 1.0.11. Reproducible production builds should pin the manifest to the tested exact version and record a controlled upgrade process.

### 5.2 Implicit runtime dependencies

The project also depends on:

- Python 3.12+ for native projects and the live worker;
- Node.js 22-era tooling for the gateway and `tsx` execution;
- the official `blocks` CLI for native checks, registration, runtime, and publishing;
- valid `BLOCKS_API_KEY` credentials in the native runtime/gateway environment;
- separate gateway client credentials (`GATEWAY_CLIENT_KEYS` and optional agent allowlists);
- filesystem access to `yield_data.csv`, generated catalog files, and optional `live_data/live_snapshot.json`;
- writable snapshot/status directories for the live worker;
- a supervised process/container host for 24/7 operation;
- DNS, TLS, outbound HTTPS, and provider availability;
- valid JSON responses and compatible schemas from Binance, Coinbase, DeFiLlama, Ethereum RPC, and Solana RPC;
- accepted private-agent invitations and A2A permissions for the orchestrator;
- the correct paid billing mode and account budget for the gateway;
- deployment-specific `.env`/secret-manager injection without exposing credentials to browser code.

### 5.3 External network and platform boundaries

The live worker uses these default external endpoints:

- Binance: `https://api.binance.com`
- Coinbase Exchange: `https://api.exchange.coinbase.com`
- DeFiLlama: `https://api.llama.fi`
- Ethereum RPC: `https://cloudflare-eth.com`
- Solana RPC: `https://api.mainnet-beta.solana.com`

The Blocks integration uses the Blocks CLI and SDK, with credentials and remote state outside the repository. Documentation links and installer URLs are not runtime dependencies of the local handlers, but they are operational dependencies for deployment and maintenance.

The external providers are not interchangeable:

- Binance is the primary market source for the supported symbol map;
- Coinbase is currently a secondary/fallback sample for BTC, ETH, and SOL;
- most assets therefore have explicit `binance_only` coverage;
- DeFiLlama supplies chain-level TVL, not a substitute for yield evidence;
- RPC observations provide chain-health context, not a complete on-chain data model.

### 5.4 Dependency risks

| Risk | Severity | Evidence / consequence |
|---|---|---|
| SDK manifest uses `latest` | High | Future install may differ from tested lockfile/runtime behavior |
| Native `blocks-network` version not pinned in the report evidence | High | Native handler behavior can vary across generated projects/environments |
| Public RPC/provider availability | High | Shared endpoints have no repository-controlled SLA; throttling/outage affects freshness |
| Live platform permissions/billing | High | Not locally reproducible; failure can occur after local tests pass |
| Missing shared live snapshot delivery in container mode | High | Paid deployments do not automatically consume worker output |
| Process-local gateway budgets | Medium | Multiple gateway instances can exceed aggregate spend intent |
| Local filesystem/process supervisor | Medium | PowerShell manager is not a full production supervisor |
| Generated mirror drift | Medium | Root `common.py` is currently ahead of deployment copies |
| Browser/static data serving | Medium | Dashboard requires correct HTTP serving and artifact availability |

## 6. Proof obligations still open

### Blocking obligations for full fleet equivalence

- [ ] Synchronize root `blocks_agents/handlers/common.py` to all 11 data-consuming deployments.
- [ ] Recompute SHA-256 equality for every shared handler and documentation artifact.
- [ ] Run each native deployment's `blocks check` with the release dependency set.
- [ ] Verify native wrapper artifact envelopes against local artifact envelopes.
- [ ] Test malformed, stale, retained, missing, and fresh live snapshots through both root and deployment handlers.
- [ ] Pin and record exact Python `blocks-network` and Node `@blocks-network/sdk` versions.
- [x] Add `sync_deployments.py --check` and CI verification for deterministic source-to-deployment hashes.
- [x] Generate standard native adapters and metadata from card contracts; keep the A2A adapter custom and explicit.
- [x] Add a guarded no-spend/private trigger utility and scaffold/materialized-package tests.

### Blocking obligations for production dependency confidence

- [ ] Run a controlled live provider canary with timestamps, schemas, HTTP status, rate-limit headers, and error handling captured.
- [ ] Reconfirm provider terms, attribution, and polling limits before production.
- [ ] Provide an explicit shared volume/distribution path if paid deployed agents must consume live data.
- [ ] Separate worker liveness from data readiness and alert on degraded/no-fresh-observation states.
- [ ] Verify Blocks registration, private invitations, A2A grants, billing mode, and paid budget externally.
- [ ] Exercise controlled private triggers for success, failure, timeout, cancellation, malformed input, and artifact download.
- [ ] Perform dependency vulnerability/licence review using the approved organization tooling.

## 7. Reproducible proof procedure

Run from the repository root in a clean operator-controlled environment:

```bash
# 1. Generate and validate derived artifacts.
python build_asset_catalog.py
python audit_csv.py

# 2. Run no-network behavior checks.
python run_live_tests.py
PYTHONDONTWRITEBYTECODE=1 python -m blocks_agents.handlers
PYTHONDONTWRITEBYTECODE=1 python blocks_deploy/crypto_yield_a2a_orchestrator/test_handler.py

# 3. Parse all repository Python and dashboard syntax.
python -m py_compile live_data.py live_worker.py blocks_agents/handlers/common.py
node --check matrix.js

# 4. Check gateway without paid dispatch.
cd crypto_yield_matrix_node_gateway
npm ci
npm run check
npm run smoke
cd ..

# 5. Recompute mirror equality; this must include common.py.
python - <<'PY'
from pathlib import Path
root = Path('.')
projects = [p for p in (root/'blocks_deploy').iterdir() if p.is_dir() and p.name != 'crypto_yield_a2a_orchestrator']
for project in projects:
    for rel in ['blocks_agents/handlers/common.py', 'blocks_agents/handlers/__main__.py']:
        assert (project/rel).read_bytes() == (root/rel).read_bytes(), (project, rel)
print('shared handler mirrors: PASS')
PY

git diff --check
```

The final proof record should attach:

- commit SHA;
- Python and Node versions;
- exact dependency lockfile hashes;
- output of every command;
- native `blocks check` results;
- private registry/card identifiers;
- provider canary timestamps and response summaries;
- live A2A permission evidence;
- approved canary budget and rollback owner.

## 8. Recommended remediation order

1. Keep the generated adapter and SHA-256 mirror checks required in CI.
2. Pin SDK dependencies and add a lockfile/version policy for all native projects.
3. Add CI checks for mirror equivalence and malformed/stale live snapshot behavior.
4. Define shared live-snapshot delivery before exposing live data to paid agents.
5. Verify external provider and Blocks behavior in a private, budgeted canary.
6. Add centralized observability, readiness alerts, and aggregate budget controls.
7. Only then reassess the public/unattended paid-production release decision.

## 9. Final decision

**Current state: PARTIAL equivalence; NO-GO for claiming full behavioral equivalence or public/unattended paid production.**

The project has a credible local proof foundation: canonical-source controls, deterministic generated artifacts, byte-identical specialized handlers, safe gateway policy tests, and dependency documentation. The decisive remaining issue is not hidden in the local specialized logic; it is synchronization and verification at shared dependency and external-runtime boundaries.

Do not describe the fleet as fully behaviorally equivalent until the common-handler mirror divergence is corrected and the open native/live obligations are evidenced.

## References

- [`audit.md`](audit.md) — production readiness decision and release gates
- [`validate.md`](validate.md) — canonical CSV and generated artifact validation
- [`audit_csv.py`](audit_csv.py) — data and mirror validator
- [`build_asset_catalog.py`](build_asset_catalog.py) — generated artifact builder
- [`blocks_agents/handlers/common.py`](blocks_agents/handlers/common.py) — shared local contract
- [`live_data.py`](live_data.py) and [`live_worker.py`](live_worker.py) — live overlay and worker
- [`crypto_yield_matrix_node_gateway/server.ts`](crypto_yield_matrix_node_gateway/server.ts) — paid gateway policy boundary
- [`setup.md`](setup.md) — Blocks deployment and operations guide
