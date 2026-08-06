# Blockchain yield expert agents

This directory contains ten local Blocks.ai-compatible agent-card manifests for the crypto yield matrix project. They are file-backed expert profiles, not published network agents. No credentials, package installation, registration, or external data access is required to use the cards as local orchestration metadata.

## Compatibility contract

Each card follows the researched Blocks agent-card shape as a local adapter contract; the included `loader.py` is the resolver for the repository-relative handler paths. Native Blocks.ai publishing may require a platform-specific wrapper or schema validation that is not present in this repository.

- `identity.agentName` uses letters, numbers, and underscores only.
- `capabilities.taskKinds` declares request handling.
- `tags` represent the agent's skills.
- `runtime.handler` points to an included local Python handler path.
- `io.inputs` accepts a JSON request with a question and file list.
- `io.outputs` returns a structured analysis artifact.

The cards reference project files rather than embedding data. Included standard-library Python handlers mount the repository read-only, reject undeclared or traversal paths, restrict access to the listed files, and return a common JSON artifact envelope with source/context provenance. The cards can be loaded locally through `blocks_agents/loader.py`; publishing or registering them requires the user's own Blocks credentials and should not be performed automatically.

## Shared file context

The primary evidence files are:

- `validate.md` — audit findings, provenance conflicts, research use cases, and modeling guardrails.
- `DATA_DICTIONARY.md` — field definitions and modeling notes.
- `yield_data.csv` and `yield_data1.csv` — conflicting source snapshots with the same schema.
- `consolidated_yield_data.csv` — both source versions appended with `source_file` and `source_row` provenance.
- `table-*.csv` — source snapshots, metadata tables, and compact summaries with heterogeneous schemas.
- `index.html`, `matrix.js`, `styles.css` — current user-facing matrix behavior and labels.

## Agents

| Card | Expert role | Primary user value |
|---|---|---|
| `data_provenance_auditor.json` | Data provenance and audit | Finds conflicts, stale metadata, and untraceable transformations. |
| `yield_methodology_expert.json` | Yield methodology | Makes APY/APR, staking, lending, inflation, and annualization comparable. |
| `crypto_risk_analyst.json` | Risk and drawdown | Compares yield against volatility, drawdown, beta, and Sharpe-like measures. |
| `defi_liquidity_analyst.json` | DeFi liquidity | Flags weakening volume, TVL, activity, and exit-risk proxies. |
| `tokenomics_sustainability_expert.json` | Tokenomics sustainability | Separates nominal yield from inflation and dilution pressure. |
| `quant_forecasting_expert.json` | Quantitative forecasting | Designs cautious, leakage-controlled yield forecasts with uncertainty. |
| `portfolio_scenario_expert.json` | Portfolio scenarios | Explains educational yield/risk/liquidity trade-offs under user constraints. |
| `model_validation_guardian.json` | Model validation | Blocks source duplication, target leakage, invalid splits, and overclaiming. |
| `matrix_research_insights_agent.json` | Dashboard research insights | Converts existing matrix metrics into traceable user-facing findings. |
| `crypto_research_communications_agent.json` | Research communication | Produces cautious, sourced, non-advisory reports with evidence locations. |

## Safety and data limitations

- The two yield source files disagree for every asset row. Never treat them as independent training observations.
- The repository contains estimated, derived, and supplied target fields. Cards must label these statuses in outputs.
- Eight quarters and 59 assets per source are suitable for prototyping and research triage, not validated production forecasting.
- Forecast cards must use chronological splits, out-of-time evaluation, simple baselines, calibrated probabilities where relevant, and uncertainty intervals.
- Agents should return `PASS`, `WARNING`, or `FAIL` status plus exact file/row/column references whenever possible.
- Outputs are research and decision-support artifacts, not financial advice or guaranteed return predictions.

## Local use

1. Select a card and send a JSON request containing `question` and optional `source_file`, `symbol`, `category`, `features`, or `target` fields.
2. Mount this repository read-only for the handler; the included handlers resolve files relative to the repository root.
3. Return the common envelope: `agent`, `status`, `summary`, `findings`, `assumptions`, `limitations`, and `provenance`.
4. Run Blocks CLI validation or publishing only after installing the official SDK/CLI and supplying the user's credentials explicitly.
5. The forecasting handler intentionally returns a readiness `FAIL` until a canonical source and additional dated history are available; this is a safety gate, not a runtime defect.

## Included handlers

The ten cards point to handlers in `blocks_agents/handlers/`. They use only the Python standard library and can be adapted to the official `blocks_network` SDK wrapper. `loader.py` resolves each manifest's `./handlers/...` path and invokes its `handler(task, ctx)` entry point. `common.py` accepts the Blocks request-part shape, validates the declared read-only context allowlist, loads CSVs, filters symbols/categories, reports status when a Blocks context is available, and emits a validated JSON artifact envelope.
