# Redundancy Scan and Improvement Opportunities

**Scan date:** 2026-08-07  
**Scope:** Repository source, deployment packages, gateway, dashboard, tests, and documentation outside `csv/`.  
**Excluded:** The entire `csv/` directory and CSV file contents. Generated/cache paths such as `.git/`, `node_modules/`, `.venv/`, `__pycache__/`, and `*.pyc` were also excluded.  
**Report-only request:** No implementation files were changed by this scan.

## Executive summary

The largest redundancy is intentional deployment mirroring: the root `blocks_agents/` scaffold is copied into all 11 data-consuming `blocks_deploy/<agent>/blocks_agents/` packages so each native Blocks.ai deployment can remain self-contained. This is compatible with paid Blocks deployment, but it creates a high synchronization burden and a large drift surface.

The scan found no evidence that the dashboard's main helpers are dead code, and the native `handler.py` and `trigger.py` files are agent-specific rather than exact duplicates. The best improvements are therefore **source-of-truth and packaging improvements**, not a broad rewrite of the research logic.

## Evidence snapshot

- **11** non-orchestrator data-consuming deployment packages were compared with the root scaffold.
- **29 shared scaffold paths** are byte-identical across the root `blocks_agents/` directory and all 11 data deployments, including `loader.py`, `README.md`, `DATA_DICTIONARY.md`, `validate.md`, `agent_cards.json`, all shared handlers, and all local agent cards.
- The shared scaffold's common functions—such as `load_card`, `run_card`, `task_payload`, `validate_context_files`, `load_source`, `select`, `report`, and `status`—are repeated in **12 copies** (root plus 11 deployment mirrors).
- The deployment adapters are not exact copies after normalization: each `blocks_deploy/<agent>/handler.py` points to a different local handler, and each trigger names a different agent or has different request behavior. They are boilerplate, but not identical business logic.
- `matrix.js` helper functions checked during the scan (`number`, `average`, `formatNumber`, `formatUsd`, and `createAssetBlock`) have active call sites. No clear dead helper was identified there.
- The A2A orchestrator is a distinct implementation and was not treated as a redundant data-bearing deployment. It intentionally remains separate from the 11 data mirrors.

## Findings

### REDUN-001 — Shared Python scaffold duplicated across 12 packages

**Severity:** High maintenance risk  
**Confidence:** High  
**Evidence:** `blocks_agents/loader.py`, `blocks_agents/handlers/common.py`, `blocks_agents/handlers/*.py`, and their identical copies under every `blocks_deploy/*/blocks_agents/` directory.

The complete local scaffold is copied into the root and each of the 11 native deployment packages. A change to validation, provenance, artifact shape, user-value guidance, or a handler must be synchronized repeatedly. A missed copy can produce different behavior between local testing and a paid deployment.

**Why this may be intentional:** Native Blocks packages commonly need their runtime dependencies available inside the deployment directory. Removing the copies without verifying the Blocks packaging/import boundary could break registration or runtime imports.

**Improvement opportunity:** Establish one authoritative source plus a deterministic packaging step that materializes each deployment bundle. Keep the generated copies for Blocks compatibility, but never edit them manually. The packaging step should:

1. Copy only the required scaffold files into each deployment.
2. Stamp a source revision/hash into a generated manifest.
3. Fail if any checked-in mirror differs from the source.
4. Run the local handler smoke test against the source and at least one materialized deployment.
5. Run `blocks check` for every native package before publishing.

**Expected value:** Fewer synchronization errors, safer paid releases, smaller review surface, and clear provenance for deployed code.

### REDUN-002 — Every data deployment carries every specialist handler

**Severity:** Medium  
**Confidence:** High  
**Evidence:** `blocks_deploy/<agent>/blocks_agents/handlers/` contains the full specialist handler set even though the package-level `handler.py` imports the deployment's named local handler, for example `blocks_deploy/crypto_risk_analyst/handler.py`.

Each native package appears to ship the common scaffold and all specialist modules, although a single specialist is the public entry point for that package. This increases package size and means an unrelated specialist change can alter many deployment bundles.

**Improvement opportunity:** Build a per-agent deployment manifest. For each native package, include only its public adapter, the common runtime helpers, the selected specialist handler, and the card/runtime files it actually needs. Retain the full 11-agent scaffold only in the local orchestration project if it is required there.

**Compatibility guard:** Confirm imports, card resolution, `blocks check`, and a private no-spend/local handler test before removing any module from a deployment. If Blocks requires the full package tree, retain the files but generate them rather than hand-maintaining them.

**Expected value:** Smaller artifacts, faster checks, reduced drift, and less accidental coupling between separately paid agents.

### REDUN-003 — Repeated deployment documentation and metadata mirrors

**Severity:** Medium  
**Confidence:** High  
**Evidence:** `blocks_agents/README.md`, `DATA_DICTIONARY.md`, `validate.md`, `agent_cards.json`, and specialist card files are duplicated throughout the 11 deployment directories.

These copies are useful as self-contained deployment context, but they repeat the same documentation and contract content many times. A documentation correction can be applied to the root while an older copy remains in a paid deployment package.

**Improvement opportunity:** Treat README, dictionary, validation report, and card metadata as generated deployment assets. Add a single `build_deployments` or equivalent synchronization command that reports:

- source-to-mirror hash mismatches;
- missing or extra files;
- deployment-specific files that are allowed to differ;
- the generated timestamp/source revision.

Avoid symlinks: they are unreliable across Windows, containers, and hosted deployment uploaders.

**Expected value:** Consistent operator instructions, fewer stale contracts, and reproducible deployment archives.

### REDUN-004 — Native adapter wrappers repeat the same forwarding pattern

**Severity:** Low  
**Confidence:** High  
**Evidence:** `blocks_deploy/*/handler.py` each import a local handler and return `local_handler(task, ctx)`.

The wrappers are intentionally small and agent-specific, but their imports, type annotations, and forwarding body are repeated. This is not a runtime defect; it is template boilerplate.

**Improvement opportunity:** Generate these adapters from the agent name in the card or maintain one clearly documented adapter template. Keep the generated `handler.py` in each package because Blocks registration expects a package-local entry point.

**Expected value:** New agents become less error-prone to add, and wrapper changes are made once.

### REDUN-005 — Trigger scripts duplicate SDK lifecycle plumbing

**Severity:** Low to medium  
**Confidence:** High  
**Evidence:** `blocks_deploy/*/trigger.py` repeat client creation, `send_message`, progress callbacks, artifact decoding/download, terminal waiting, session closing, and client destruction. The exact scripts differ by agent and request payload, so this is shared lifecycle logic rather than exact-file duplication.

**Improvement opportunity:** Add a local, non-production `trigger_support.py` utility with shared functions for:

- creating the client;
- registering progress/artifact/terminal callbacks;
- decoding inline or downloaded artifacts;
- bounded waiting and cleanup;
- clearly selecting `billingMode` and no-spend versus paid behavior.

Each trigger should retain only agent name and request payload configuration. Put an explicit warning in the utility that normal smoke tests must use a fake client and that a real trigger is paid.

**Expected value:** Consistent cleanup and timeout behavior, fewer copy/paste defects, and clearer separation between test plumbing and paid execution.

### REDUN-006 — Repeated request-to-report orchestration in specialist handlers

**Severity:** Low  
**Confidence:** Medium  
**Evidence:** Most handlers repeat the sequence `task_payload` → `source_file` → `load_source` → `select` → `status` → build `findings` → `report`, for example `crypto_risk_analyst.py`, `defi_liquidity_analyst.py`, `portfolio_scenario_expert.py`, and `yield_methodology_expert.py`.

The findings are domain-specific, so the repeated outer structure is understandable. Over-abstracting it could make the research logic harder to audit.

**Improvement opportunity:** Add a small helper only for the shared setup (`selected_source_rows(payload, status_message, ctx)`), while leaving each specialist's finding construction explicit. Do not hide domain formulas behind a generic callback framework unless tests prove it improves clarity.

**Expected value:** Uniform source validation and status behavior with minimal loss of auditability.

### REDUN-007 — Numeric parsing semantics are split between `value` and `numeric_value`

**Severity:** Medium correctness opportunity  
**Confidence:** High  
**Evidence:** `blocks_agents/handlers/common.py` exposes both `value()` and `numeric_value()`. `value()` converts missing/invalid values to `0.0`, while `numeric_value()` returns `None`; handlers use both conventions.

This is not duplicate code in the strict sense, but it duplicates the concept of numeric field access with different missing-data semantics. A user can receive a displayed zero in one analysis and an unavailable/null feature in another.

**Improvement opportunity:** Define an explicit field-access policy, such as:

- `required_number()` for fields where missing data should fail or create a warning;
- `optional_number()` returning `None`;
- `display_number()` only for presentation with a documented fallback.

Update handler findings and limitations to preserve the distinction between an actual zero and unavailable data.

**Expected value:** More trustworthy user-facing research and fewer false signals caused by silent zero substitution.

### REDUN-008 — Canonical contract values are repeated in validation, documentation, and audit text

**Severity:** Medium maintenance risk  
**Confidence:** High  
**Evidence:** `audit_csv.py` hardcodes expected row/column counts (`118` and `61`), while `DATA_DICTIONARY.md`, `validate.md`, `audit.md`, and setup documentation repeat dataset and deployment counts.

Hardcoded contract values are useful as guardrails, but the same facts are maintained in multiple places. A dataset contract change can leave contradictory documentation.

**Improvement opportunity:** Keep invariant expectations in one machine-readable schema/contract file and generate the validation report and summary counts from it. Continue asserting expected counts in CI, but derive descriptive counts from the canonical file rather than manually rewriting prose. Generate deployment counts from discovered packages.

**Expected value:** Less documentation drift and clearer release diffs when the canonical dataset evolves.

### REDUN-009 — Paid gateway configuration text has small drift potential

**Severity:** Low  
**Confidence:** Medium  
**Evidence:** `crypto_yield_matrix_node_gateway/server.ts` owns the `BILLING_MODE` and task-cost constants, while `index.ts` and README/setup text repeat paid billing and `$0.10/task` descriptions.

This is mostly intentional documentation, but a price or billing-mode change can make logs, README examples, and runtime policy disagree.

**Improvement opportunity:** Expose a single non-secret runtime metadata object for health/agents/docs generation, or at least centralize the displayed task cost and billing label in one module. Keep the SDK call configured with `billingMode: 'paid'` and test that the gateway still uses the paid mode required by the published agents.

**Expected value:** Fewer misleading operator messages and safer paid-cost communication.

### REDUN-010 — Stale provenance/source wording creates duplicate or conflicting concepts

**Severity:** Medium user-value opportunity  
**Confidence:** High  
**Evidence:** Several current handler strings refer to old source concepts, including:

- `blocks_agents/handlers/crypto_risk_analyst.py` limitation mentioning `table-1786044184987.csv`;
- `blocks_agents/handlers/matrix_research_insights_agent.py` saying the UI can select another source even though `YIELD_SOURCES` accepts only `yield_data.csv`;
- repeated historical provenance labels such as `yield_data1.csv` appearing in metadata/documentation even though the file is not a permitted dataset.

These are not executable duplicate algorithms, but they repeat obsolete source vocabulary and can confuse users about what data is actually loaded.

**Improvement opportunity:** Use one canonical source label in user-facing messages (`yield_data.csv`), describe historical labels only under provenance metadata, and link limitations to `DATA_DICTIONARY.md`/`validate.md` rather than to excluded or historical filenames.

**Expected value:** Better traceability, fewer mistaken requests for removed files, and clearer research interpretation.

## Improvement roadmap

### Priority 1 — Safe now, preserves paid Blocks compatibility

1. Add a deterministic mirror/packaging command and a CI check for source-to-deployment hashes.
2. Generate native adapter wrappers and deployment metadata from the existing agent cards.
3. Add a trigger support utility for local/private triggers with explicit paid-task warnings.
4. Add tests that exercise the source scaffold and one materialized deployment package.
5. Correct stale source wording and make missing numeric values explicit in artifacts.

### Priority 2 — Validate before rollout

1. Produce minimal per-agent deployment bundles and run imports plus `blocks check` for every package.
2. Verify private registration and a controlled paid canary after packaging changes.
3. Confirm A2A permissions and artifact behavior are unchanged.
4. Compare package sizes and startup time before and after pruning unused specialist modules.

### Priority 3 — Operational scaling

1. Replace the process-local gateway budget ledger with a shared quota service before running multiple gateway instances.
2. Centralize structured logs, metrics, spend alerts, and deployment revision identifiers.
3. Keep the gateway's single-instance paid-budget assumption explicit until shared accounting is deployed.

## Not classified as redundant

- `crypto_yield_matrix_node_gateway/server.ts` and `index.ts` have separate responsibilities: HTTP/business policy versus process configuration/startup.
- The A2A orchestrator is distinct from specialist handlers because it dispatches, times out, cancels, and merges remote tasks.
- Domain-specific specialist finding construction is different research logic even when the surrounding report envelope is shared.
- `matrix.js` helpers checked in this scan have active call sites; no dead helper was reported.
- The repeated deployment files are not automatically safe to delete: self-contained native Blocks packages may require local copies for registration and runtime resolution.

## Method limitations

This was a static redundancy scan, not a behavioral equivalence proof, dependency audit, or live Blocks deployment test. It did not inspect the contents of `csv/` by request. It did not run paid tasks, publish agents, or change deployment state. Before removing or consolidating any mirrored file, validate the result with local no-spend tests, native `blocks check`, private registration, and an explicitly budgeted canary.
