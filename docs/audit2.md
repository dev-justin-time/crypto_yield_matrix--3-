# Platform File Audit — `audit2.md`

**Project:** Crypto Yield Matrix / Blocks.ai agent fleet
**Audit date:** 2026-08-08
**Audit method:** Full read-only repository inspection, every automated test suite executed, all deployment/handler/gateway checks run, manual code review of every platform Python and TypeScript file
**Auditor:** Buffy (Freebuff)
**Status:** All code-level findings resolved; two external production gates remain

---

## 1. Executive Summary

**Verdict: PLATFORM HEALTHY — 0 actionable code bugs remaining**

All 15 automated check suites pass green. The repository has strong local integrity: canonical CSV contracts, byte-identical handler mirrors, deterministic generated artifacts, passing gateway smoke/resilience tests, and all 11 local agent handlers smoke-clean. Four code-level findings were discovered and **all have been fixed**. Two external production gates (budget persistence across instances, live provider canary) remain as documented blockers carried forward from the prior `audit.md`.

---

## 2. Automated Test Suite Results

### 2.1 All checks green (15/15)

| # | Check | Result | Details |
|---|-------|--------|---------|
| 1 | `audit_csv.py` | **PASS** | 118 rows, 61 columns, 0 issues, 11 deployment copies verified |
| 2 | `fleet_gate.py` | **PASS** | 12 native projects, all required files present, local preflight ready |
| 3 | `generate_deployments.py --check` | **PASS** | 0 differences; all 23 adapter/metadata files current |
| 4 | `sync_deployments.py --check` | **PASS** | 0 missing, 0 mismatched (fixed FI-001) |
| 5 | `run_live_tests.py` | **PASS** | 5/5 tests pass (symbols, collector, URLs, merge, freshness) |
| 6 | `python -m blocks_agents.handlers` | **PASS** | 11 agent cards smoke-tested successfully |
| 7 | `blocks_deploy/.../test_handler.py` | **PASS** | A2A orchestrator mocked merge/timeout tests pass |
| 8 | Python AST parse | **PASS** | 2,506 files parse without syntax errors |
| 9 | `npm run check` (gateway tsconfig) | **PASS** | TypeScript strict-mode type-check passes |
| 10 | `npm run smoke` | **PASS** | Auth, readiness, metrics, health, validation, 12 agents — no paid dispatch |
| 11 | `npm run resilience` | **PASS** | Capacity, timeout, metrics, artifact cap — no spend |
| 12 | `node --check matrix.js` | **PASS** | Dashboard JavaScript syntax valid |
| 13 | `git diff --check` | **PASS** | No whitespace errors |
| 14 | `organize_csv_sources.py --check` | **PASS** | 15 named source files verified |
| 15 | `test_packaging.py` | **PASS** | 10/10 tests OK |

---

## 3. Findings

### FI-001 — Deployment mirror drift (11 `validate.md` + manifest) ✅ RESOLVED

**Severity:** Low | **Fix:** `python sync_deployments.py --write` — synced 171 source files to 11 deployments, regenerated manifest.

### FI-002 — Duplicate unreachable `except HTTPError` handler in `live_data.py` ✅ RESOLVED

**Severity:** Low | **Fix:** Removed the second duplicate `except HTTPError as error:` block in `_blockchain()` — dead code eliminated.

### FI-003 — `release_gate.py` template produces invalid placeholder values ✅ RESOLVED

**Severity:** Low | **Fix:** `template()` now emits `paid_canary_max_approved_spend: 0` and `actual_task_count_and_spend: {"task_count": 0, "spend_usd": 0}` instead of empty strings.

### FI-004 — `BINANCE_SYMBOLS` coverage gap vs. canonical symbols ✅ RESOLVED

**Severity:** Low | **Fix:** Added missing tickers: `SUIUSDT`, `APTUSDT`, `RENDERUSDT`, `TAOUSDT`, `XTZUSDT`. Now 59/59 canonical symbols covered.

---

## 4. Open External Gates

### FI-005 — Gateway budget state not durable across restarts

**Severity:** Medium | **Status:** External — carried forward from `audit.md` CR-003/HI-003

The gateway persists budget to a local file and resets daily, but multiple instances or container restarts without a persistent volume would lose state. Enforce exactly one gateway instance or deploy a shared atomic quota ledger.

### FI-006 — No live provider canary evidence

**Severity:** High | **Status:** External — carried forward from `audit.md` CR-001

Fixture canary passes (5/5), but no live canary has been executed with `--live --confirm-live`. Run: `python live_canary.py --live --confirm-live`.

---

## 5. Code Quality Observations

### Strengths

- **Complete dependency documentation:** `docs/familytree.md` maps every file's imports, reads, writes, and dependents in a directory-styled treemap — making onboarding, refactoring, and impact analysis straightforward.
- **Strong defensive coding:** Common handler validates context filenames against an explicit allowlist, prevents path traversal, marks unavailable values as `null` rather than zero, never makes network calls from paid tasks.
- **Gatekeeper pattern:** `trigger_guarded.py` requires `--live` AND `--confirm-paid` plus `BLOCKS_API_KEY` before any paid dispatch.
- **Atomic writes:** Both `live_worker.py` and `release_gate.py` use `tempfile + rename` for atomic file writes.
- **Safe budget semantics:** Gateway conservatively reserves budget before dispatch, preventing overspend from uncertain outcomes.
- **Deterministic builds:** `generate_deployments.py` and `sync_deployments.py` provide hash-verified deterministic mirroring.
- **LLM hardening:** Gateway validates hosted endpoints resolve to public IPs only, enforces HTTPS, requires configured allowlists, caps response sizes.
- **Complete Binance coverage:** All 59 canonical symbols now have Binance ticker mappings for live price observations.

---

## 6. Risk Matrix

| Risk | Severity | Status |
|------|----------|--------|
| Live Blocks platform unverified | High | External gate |
| No production TLS/edge/firewall | High | External gate |
| Budget not safe for horizontal scaling | Medium | External gate |
| No live provider canary (FI-006) | High | External gate |
| ~~Mirror drift (FI-001)~~ | — | ✅ Fixed |
| ~~Duplicate except handler (FI-002)~~ | — | ✅ Fixed |
| ~~Template blank values (FI-003)~~ | — | ✅ Fixed |
| ~~Binance coverage gap (FI-004)~~ | — | ✅ Fixed |

---

## 7. Reproduction Commands

Full audit suite (no-spend, no network):

```bash
python audit_csv.py
python organize_csv_sources.py --check
python fleet_gate.py
python generate_deployments.py --check
python sync_deployments.py --check
python run_live_tests.py
python -m blocks_agents.handlers
python blocks_deploy/crypto_yield_a2a_orchestrator/test_handler.py
python live_canary.py --fixture
python test_packaging.py
cd crypto_yield_matrix_node_gateway && npm run check && npm run smoke && npm run resilience
node --check matrix.js
git diff --check
```
