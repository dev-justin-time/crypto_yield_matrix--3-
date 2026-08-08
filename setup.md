# Blocks.ai setup guide

This guide explains how to use the crypto-yield-matrix expert agents locally and how to connect a native Provider project to the Blocks Network.

It is based on the official Blocks.ai documentation:

- [Blocks documentation](https://blocks.ai/docs)
- [Quickstart](https://blocks.ai/docs/quickstart)
- [Key concepts](https://blocks.ai/docs/key-concepts)
- [Authentication reference](https://blocks.ai/docs/authentication)

> **Important:** `blocks_agents/` is currently a local, file-backed adapter scaffold. It contains eleven agent cards, including a feature-engineering expert, standard-library Python handlers, and `blocks_agents/loader.py`, but it is not registered or published on Blocks Network. Do not place API keys in this repository or publish the cards until the native Blocks project wrapper has been created and tested.

## 1. What this project provides

The repository contains eleven blockchain and cryptocurrency research agents:

| Agent | Purpose |
|---|---|
| `data_provenance_auditor` | Audits schemas, source conflicts, hashes, and lineage. |
| `yield_methodology_expert` | Compares yield mechanisms, annualization, and methodology notes. |
| `crypto_risk_analyst` | Places yield beside volatility, drawdown, beta, and Sharpe-like metrics. |
| `defi_liquidity_analyst` | Reviews volume, TVL, addresses, transactions, and liquidity proxies. |
| `tokenomics_sustainability_expert` | Compares nominal yield with inflation and dilution pressure. |
| `quant_forecasting_expert` | Designs cautious forecasts and enforces readiness gates. |
| `portfolio_scenario_expert` | Explains educational yield/risk/liquidity scenarios. |
| `model_validation_guardian` | Checks duplicate provenance rows, leakage, target circularity, and time splits. |
| `matrix_research_insights_agent` | Converts the dashboard matrix into traceable research insights. |
| `crypto_research_communications_agent` | Produces cautious, evidence-linked research notes. |
| `feature_engineering_expert` | Recomputes four transparent derived yield, liquidity, risk, and peer features. |

The index is [`blocks_agents/agent_cards.json`](blocks_agents/agent_cards.json). The local loader resolves each manifest's `./handlers/...` path and calls its `handler(task, ctx)` function. The feature agent computes `yield_momentum`, `mcap_to_tvl`, `risk_score`, and `yield_premium` from source fields and preserves warnings for undefined ratios.

## 2. Requirements

For the local scaffold:

- Python 3.12 or newer is recommended.
- No third-party Python package is required.
- The repository should be mounted read-only when handlers are run as an agent service.

For a native Blocks Provider project, the official Quickstart lists:

- Node.js 22 or newer, **or** Python 3.12 or newer.
- npm 9 or newer when installing the CLI through npm.
- The latest Blocks CLI.
- A Blocks account and an organization for registration/publishing.

The existing local scaffold does not include a CLI-generated `pyproject.toml`, `.env`, `trigger.py`, or native `blocks_network` SDK dependency. Those are created by the official Provider scaffold and should be kept separate from the local validation layer until integration is deliberate. The native Blocks adapter described later is a future integration plan; it is not currently implemented in this repository.

## 3. Run the local agents first

From the repository root, use the local loader and smoke test before connecting to any external service:

```bash
python -m py_compile blocks_agents/*.py blocks_agents/handlers/*.py
python -m blocks_agents.handlers
```

The smoke test loads all eleven cards from `blocks_agents/agent_cards.json`, invokes each handler, and checks that it returns a JSON artifact. The feature-engineering handler is also checked against the four documented formulas.

### Invoke one local card

A minimal Python caller can use the loader with a Blocks-shaped task object. For reproducible results, always provide `source_file`; if omitted, local data handlers default to `yield_data.csv`.

```python
import json
from blocks_agents.loader import load_card

class Part:
    def __init__(self, text):
        self.text = text

class Task:
    def __init__(self, payload):
        self.request_parts = [Part(json.dumps(payload))]

_, handler = load_card("crypto_risk_analyst.json")
result = handler(Task({
    "question": "Compare BTC yield and downside context",
    "symbol": "BTC",
    "source_file": "yield_data.csv",
}))
print(result["artifacts"][0]["data"])
```

### Local request fields

Handlers accept a JSON object in the first `request` part. Common fields are:

- `question` — the user’s question.
- `source_file` — `yield_data.csv` or `yield_data.csv`.
- `symbol` — an asset symbol such as `BTC`.
- `category` — an asset category filter.
- `files` — optional repository context files from the declared allowlist.
- `features`, `target`, and `split` — used by validation and forecasting agents.

The handlers reject undeclared paths, absolute paths, traversal paths, and invalid source filenames. Their outputs contain `agent`, `status`, `summary`, `findings`, `assumptions`, `limitations`, and `provenance`.

## 4. Understand the data boundary before publishing

The project data has important limitations documented in [`validate.md`](validate.md):

1. `yield_data.csv` and `yield_data.csv` have the same schema but disagree for every asset row.
2. `yield_data.csv` preserves the supplied 118 rows; it is not automatically a canonical modeling table.
3. The data includes source-like, estimated, derived, and supplied target fields.
4. The current panel has only eight quarterly yield observations per asset.
5. **Corrected forecasting caveat:** The current dataset is not suitable for validated production forecasting until source identity is resolved, additional dated observations are added, leakage-controlled walk-forward testing is performed, and independently observed outcomes are available. The full audit wording is maintained in [`validate.md`](validate.md).

Do not publish an agent that presents these files as live market data, guaranteed returns, or validated investment advice. Keep the current `WARNING` and `FAIL` statuses where the handlers intentionally expose unresolved data or model-readiness issues.

## 5. Install the Blocks CLI

The official Quickstart provides three installation routes.

### npm installation

```bash
npm install -g @blocks-network/cli
blocks --version
```

### macOS, Linux, WSL, or Git Bash on Windows

```bash
curl -fsSL https://config.blocks.ai/install.sh | sh
blocks --version
```

### Native Windows PowerShell

The POSIX shell installer is not intended for native PowerShell or Command Prompt. Use the official PowerShell installer:

```powershell
irm https://config.blocks.ai/install.ps1 | iex
blocks --version
```

If Windows cannot find `blocks` after installation, the official Quickstart says the binary is placed in `%USERPROFILE%\\.blocks\\bin\\blocks.exe`. Add that directory to the user PATH and open a new terminal. The documentation provides this safer user-scoped PowerShell approach:

```powershell
$blocksPath = "$env:USERPROFILE\\.blocks\\bin"
$current = [Environment]::GetEnvironmentVariable("Path", "User")
if ($current -notlike "*$blocksPath*") {
  [Environment]::SetEnvironmentVariable("Path", "$current;$blocksPath", "User")
}
```

## 6. Create a native Provider project

Blocks distinguishes a **Provider** (the agent builder/runtime) from a **Consumer** (the caller). Choose Provider because these crypto research agents receive tasks and return artifacts.

Use a globally unique agent name. Blocks requires `agentName` to contain only letters, numbers, and underscores; hyphens are not allowed.

```bash
blocks init crypto_yield_matrix_provider_12345 --mode provider --yes --language python
cd crypto_yield_matrix_provider_12345
```

The CLI-generated Provider project includes a native handler, trigger script, `agent-card.json`, `.env`, `.gitignore`, and Python project metadata. Keep the generated native project separate from the repository’s local `blocks_agents/` package until the handler adapter has been implemented and tested.

### Install native Python dependencies

The official Quickstart recommends a virtual environment and editable install:

```bash
python -m venv .venv
```

On macOS/Linux/WSL/Git Bash:

```bash
source .venv/bin/activate
pip install -e .
```

On Windows Command Prompt:

```bat
.venv\\Scripts\\activate.bat
pip install -e .
```

On Windows PowerShell:

```powershell
.venv\\Scripts\\Activate.ps1
pip install -e .
```

Do not install packages globally for this repository. Keep the Blocks SDK inside the native Provider project’s virtual environment.

## 7. Adapt one local handler to the native Blocks SDK

The official Blocks Python handler shape receives a task and optional context, then returns an artifact envelope:

```python
from __future__ import annotations

from typing import Optional
from blocks_network import StartTaskMessage, TaskContext


def handler(
    task: StartTaskMessage,
    ctx: Optional[TaskContext] = None,
) -> dict:
    text = ""
    for part in task.request_parts:
        if part.text is not None:
            text = str(part.text)
            break

    if ctx is not None:
        ctx.report_status(f"Processing: {text}")

    return {
        "artifacts": [
            {"data": f"Result: {text}", "mimeType": "text/plain"}
        ]
    }
```

When a future native adapter is implemented, it should:

1. Parse the first `request` part as JSON.
2. Call the selected local expert logic.
3. Mount the repository read-only.
4. Preserve the local allowlist in `blocks_agents/handlers/common.py`.
5. Return the local common envelope as JSON inside a Blocks artifact.
6. Never expose `BLOCKS_API_KEY` or unrestricted filesystem access to a caller.
7. Keep the source/version warning in every research result.

The local handlers currently import from `blocks_agents.handlers.common`; they are intentionally independent of the external SDK. A native wrapper should translate between the Blocks SDK task types and this local handler contract rather than silently rewriting the data logic.

## 8. Review the native agent card

The official card describes identity, capabilities, inputs, outputs, tags, and runtime configuration. A minimal Python card has this shape:

```json
{
  "identity": {
    "agentName": "crypto_yield_matrix_provider_12345",
    "displayName": "Crypto Yield Matrix Research",
    "description": "File-backed crypto yield and risk research",
    "version": "1.0.0",
    "provider": { "organization": "Your Organization" }
  },
  "capabilities": { "taskKinds": ["request"] },
  "tags": [{ "id": "crypto_research", "name": "Crypto research" }],
  "runtime": { "handler": "./handler.py" },
  "io": {
    "inputs": [
      {
        "id": "request",
        "description": "A JSON research request",
        "contentType": "application/json",
        "required": true
      }
    ],
    "outputs": [
      {
        "id": "research_report",
        "description": "Evidence-linked research artifact",
        "contentType": "application/json",
        "guaranteed": true
      }
    ]
  }
}
```

The `request` input ID matters. Callers must send a request part whose `partId` is exactly `request`; a mismatched part ID is rejected by the backend. Run the Blocks validator against the CLI-generated native Provider project before registration. This validates the native project/card; it does not validate the custom `blocks_agents/agent_cards.json` index or the repository-relative local loader contract:

```bash
blocks check
```

The existing eleven local cards are useful design references, but the native Provider card should be generated or validated by the installed Blocks CLI because the local scaffold is not a substitute for the platform’s complete schema validator.

## 9. Authenticate safely

Authenticate from the native Provider project:

```bash
blocks login --write-env
```

The official authentication reference says this opens browser OAuth through Google or GitHub, selects the active organization when necessary, stores the CLI profile, and writes `BLOCKS_API_KEY` to the project `.env` file.

On macOS/Linux, credentials are stored under:

```text
~/.config/blocks/contexts.json
```

On Windows, they are stored under:

```text
%USERPROFILE%\\.config\\blocks\\contexts.json
```

### Credential rules

- Never commit `.env` or `BLOCKS_API_KEY`; confirm `.env` is listed in the native project’s `.gitignore` and verify with `git ls-files` that no existing secret file is tracked.
- Use [`.env.example`](.env.example) as the blank local template; it contains no credential.
- The local setup mirrors the key into each deployed project for development convenience only. In production, do not duplicate long-lived keys across project directories: inject `BLOCKS_API_KEY` through the deployment platform’s secret manager at runtime rather than storing it in a checked-in file, image layer, or shared artifact.
- If a key was ever committed, backed up, or shared, disable it in Blocks and rotate it; ignore rules and local permissions cannot remove historical exposure.
- Do not put an API key in browser JavaScript or a client bundle.
- Use a server-side token endpoint or custom token provider for browser/mobile callers.
- `blocks logout` removes local credentials but does not revoke the server-side key; disable a suspected leaked key from the Blocks dashboard.
- API keys have a default one-year TTL according to the authentication reference. Plan rotation before expiry.
- For macOS/Linux/WSL/Git Bash CI, the official documentation supports non-interactive login by piping the key through stdin:

```bash
echo "$BLOCKS_API_KEY" | blocks login --api-key-stdin --write-env
```

On Windows PowerShell, pass the secret through the equivalent pipeline without printing it:

```powershell
$env:BLOCKS_API_KEY | blocks login --api-key-stdin --write-env
```

Treat the key as a secret in CI and deployment settings, not as a repository file. Prefer the CI/deployment secret manager over generating a persistent `.env` file in a build artifact. For a Windows service, grant the `.env` or injected-secret access only to the service identity that runs `blocks run`; the current local ACL is intentionally limited to the interactive setup user and may not be sufficient for a service account.

## 10. Register privately before publishing

Register the native Provider project as private and free first:

```bash
blocks register
```

Private agents are accessible only to the owner and explicitly invited users or organizations. This is the correct phase for testing data boundaries, source warnings, output quality, and failure behavior.

If card metadata changes while the agent remains private and free, run `blocks register` again. Card changes are not synchronized automatically.

## 11. Run and test the agent

Start the native Provider runtime:

```bash
blocks run
```

Keep this process running. In a second terminal, activate the same virtual environment and run the generated trigger:

```bash
python trigger.py
```

The official Quickstart says a successful trigger should complete with a task result such as `[done] Task complete`.

Test at least these cases before inviting anyone:

1. A valid BTC request using `yield_data.csv`.
2. A valid request using `yield_data.csv` that clearly labels the alternate source.
3. A request with an invalid `source_file`.
4. A request containing `../` or an absolute path.
5. A request that asks for a forecast; verify the readiness `FAIL` gate remains visible.
6. A request that attempts to use both embedded provenance rows as independent training data.
7. A request with an unknown symbol or category.
8. A large output artifact and a normal small output artifact.

The key concepts documentation states that request tasks are single request/response work units, and that artifacts may be text, JSON, or files. Artifacts under 16 KB are delivered inline; larger artifacts are referenced externally and can be downloaded through the SDK.

## 12. Invite collaborators

Keep the agent private while testing. When a collaborator needs access, use the CLI invitation flow described by the official docs:

```bash
blocks invite send crypto_yield_matrix_provider_12345 --email user@example.com
```

The recipient must accept the invitation before they can call the private agent. Access can also be managed through the Blocks dashboard.

## 13. Publish only after private validation

When the native Provider is stable and the data limitations are visible in its output, publish with explicit settings:

```bash
blocks publish --billing-mode free --listing public --accept-terms
```

Use private listing while testing:

```bash
blocks publish --billing-mode free --listing private --accept-terms
```

The official key concepts documentation distinguishes:

- **Public** — discoverable in the Blocks Network catalog and callable by anyone subject to platform rules and quotas.
- **Private** — accessible only to the owner and granted users, organizations, or agents.

Do not switch this project to paid billing or public visibility without confirming that the agent’s descriptions, source provenance, risk disclaimers, and output limits are accurate. Publishing is an external action and requires the owner’s explicit credentials and acceptance of the platform terms.

## 14. Calling a published agent from an application

For backend callers, the official authentication reference supports an API-key-based `TaskClient`. Keep the key server-side. For browser/mobile applications, use a server-side token endpoint or custom token provider so the Blocks API key never enters the browser bundle.

A TypeScript caller follows the official SDK pattern:

```typescript
import 'dotenv/config';
import { TaskClient, textPart } from '@blocks-network/sdk';

const client = await TaskClient.create({
  billingMode: 'free',
  apiKey: process.env.BLOCKS_API_KEY,
});

const session = await client.sendMessage({
  agentName: 'crypto_yield_matrix_provider_12345',
  requestParts: [
    textPart(
      JSON.stringify({
        question: 'Compare BTC yield and downside context',
        symbol: 'BTC',
        source_file: 'yield_data.csv',
      }),
      'request',
    ),
  ],
});

session.onProgress((event) => console.log('Progress:', event.message));
const terminal = await session.waitForTerminal(30_000);
console.log('Done:', terminal.state);
session.close();
client.destroy();
```

For a browser/mobile app, replace the API-key configuration with a protected token endpoint. The proxy must authenticate your application user before requesting a Blocks consumer token; an unprotected proxy could allow anyone to consume your quota.

## 15. Agent-to-agent (A2A) orchestration

The repository now includes a native Blocks Provider project at `blocks_deploy/crypto_yield_a2a_orchestrator/`. It calls these private specialists in parallel through `TaskContext.task_client`:

- `data_provenance_auditor`
- `feature_engineering_expert`
- `crypto_risk_analyst`
- `defi_liquidity_analyst`
- `tokenomics_sustainability_expert`

The orchestrator uses the Python SDK's `SendMessageRequestPart`, omits `ownerId`, applies a 30-second specialist timeout, cancels timed-out specialist sessions on a best-effort basis, cleans up late send results, downloads non-inline artifacts, tolerates terminal/artifact event reordering, and merges partial failures into one JSON artifact.

### Local A2A validation

```bash
cd blocks_deploy/crypto_yield_a2a_orchestrator
.venv/Scripts/python test_handler.py
```

After installing the Blocks CLI, run `blocks check` from the native orchestrator project and confirm it passes for your installed CLI/schema. This repository session cannot verify that command because the `blocks` binary is not on PATH. Test the deployed orchestrator with:

```bash
python trigger.py
```

### Restart provider runtimes and the gateway on Windows

The repository-root [`Restart-BlocksAgents.ps1`](Restart-BlocksAgents.ps1) manages the local `blocks run` processes for the native deployments **and** the all-agent Node gateway (`crypto_yield_matrix_node_gateway`). It targets only PIDs previously recorded by that script, so it does not terminate unrelated Blocks or Node processes.

From PowerShell at the repository root:

```powershell
# Restart all provider runtimes plus the Node gateway (the default).
.\\Restart-BlocksAgents.ps1

# Restart one provider only (the gateway is left untouched).
.\\Restart-BlocksAgents.ps1 -AgentName crypto_risk_analyst

# Manage only the Node gateway process.
.\\Restart-BlocksAgents.ps1 -AgentName gateway

# Restart the providers but not the gateway.
.\\Restart-BlocksAgents.ps1 -SkipGateway

# Stop managed runtimes without starting them again.
.\\Restart-BlocksAgents.ps1 -StopOnly

# Preview which processes would be stopped/started.
.\\Restart-BlocksAgents.ps1 -WhatIf
```

Process output is written to `blocks-agent-logs/<name>/stdout.log` and `stderr.log` (including `blocks-agent-logs/gateway/`); PID state is stored in the ignored `.blocks-agent-state.json`. The script uses the installed native Blocks CLI for providers and the `node` on PATH for the gateway, and expects authentication to remain available in the projects' ignored `.env` files. It does not publish, register, or change billing settings. Before the first run, stop any provider runtimes started manually with `blocks run`; the script intentionally does not discover or terminate unmanaged processes.

Real (non-`-WhatIf`) runs prompt for confirmation on each stop/start action because the script declares `ConfirmImpact = 'High'`. For automated or scheduled invocations, set `$ConfirmPreference = 'None'` first (or answer the prompts interactively), otherwise the run will pause waiting for confirmation.

### Private-agent permissions

The orchestrator and specialists are private agents. A user invitation does not grant A2A access. Each specialist must invite the orchestrator machine identity:

```bash
blocks invite send data_provenance_auditor --email crypto_yield_a2a_orchestrator@blocks.ai
blocks invite send feature_engineering_expert --email crypto_yield_a2a_orchestrator@blocks.ai
blocks invite send crypto_risk_analyst --email crypto_yield_a2a_orchestrator@blocks.ai
blocks invite send defi_liquidity_analyst --email crypto_yield_a2a_orchestrator@blocks.ai
blocks invite send tokenomics_sustainability_expert --email crypto_yield_a2a_orchestrator@blocks.ai
```

These invitations have been sent and are currently pending. The target machine identity must accept each invitation before network A2A calls can succeed. The current CLI has no local workflow to auto-accept an invitation on behalf of the orchestrator machine identity; A2A remains unavailable until all five pending invitations become active. Check state with:

```bash
blocks invite grants data_provenance_auditor
blocks invite list data_provenance_auditor
```

The CLI accepts invitations with `blocks invite accept <token>`. The token must be accepted by the invitee identity; do not substitute the invitation ID, and do not publish the agents publicly to bypass private access controls.

## 16. Paid production performance profile

The deployed cards now use a bounded paid-runtime profile:

| Agent tier | `concurrency` | `maxPendingBacklog` | `maxRunningTimeSec` | Reason |
|---|---:|---:|---:|---|
| Eleven independent specialists | 4 | 20 | 45 | Four parallel tasks per instance improves throughput while keeping queue growth and runaway billing bounded. |
| `crypto_yield_a2a_orchestrator` | 2 | 8 | 90 | Two concurrent orchestrations are enough to overlap requests without multiplying five-specialist fan-outs uncontrollably. |

`expectedInstances` remains `1` as the conservative starting point. Increase it only after observing CPU/memory usage, task latency, provider rate limits, and spend. The orchestrator's five specialist calls already run in parallel; do not increase its instance count and concurrency simultaneously without load-test evidence.

The Node gateway uses one shared paid `TaskClient`, validates the required `question` locally, and limits in-flight billable tasks with `GATEWAY_MAX_CONCURRENT_TASKS=8` (process-local and best-effort; the Blocks provider backlog remains authoritative). It does not retry `sendMessage` at the application layer: retrying after an uncertain network outcome can create duplicate paid tasks. If a task wait times out, the gateway makes a best-effort remote cancel before returning 504. Send a stable `X-Idempotency-Key` header when your caller may retry an uncertain request; the key is forwarded to Blocks.

### Paid publish sequence

Publishing changes the external Blocks registry and may incur billing or platform obligations, so run these commands manually only after credentials, descriptions, provenance warnings, and pricing have been reviewed:

```bash
# In each blocks_deploy/<agent>/ project:
blocks check
blocks login --write-env
blocks register
blocks run

# After private trigger tests pass, publish explicitly as paid.
# Confirm the exact flags with `blocks publish --help` for your installed CLI:
blocks publish --billing-mode paid --listing private --price-per-task 0.10 --accept-terms
```

Use `--listing public` only after the private fleet is stable. The `billingMode` used by the gateway must match the live registry configuration; a paid target requires the gateway's `billingMode: 'paid'`. Do not run publish/register from this assistant session, and do not use a real trigger as a performance test unless you explicitly accept the per-task charge.

## 17. Operational checklist

### Before registration

- [ ] `python -m blocks_agents.handlers` passes locally.
- [ ] Native Provider project has a virtual environment and installed dependencies.
- [ ] `blocks check` passes for the native card.
- [ ] `request` is the declared input part ID.
- [ ] Handler returns at least one valid artifact.
- [ ] `.env` and API keys are ignored by Git.
- [ ] Source allowlist rejects traversal and undeclared files.

### Before inviting users

- [ ] Private registration succeeds.
- [ ] `blocks run` stays connected.
- [ ] Trigger test completes.
- [ ] Invalid source and path requests fail safely.
- [ ] Both yield versions are labeled as conflicting alternatives.
- [ ] Forecast requests remain blocked until the documented data gates are met.
- [ ] Outputs contain evidence, assumptions, limitations, and provenance.

### Before public publishing

- [ ] The native card description does not claim live data or validated forecasts.
- [ ] The public listing explains that outputs are research/decision support, not financial advice.
- [ ] The data refresh policy and source dates are documented.
- [ ] Large artifacts and task failures are handled.
- [ ] Credential rotation and monitoring procedures are documented.
- [ ] Public/private listing and free/paid billing flags are explicitly reviewed.

## 18. Troubleshooting

### `blocks` is not found

- Run `blocks --version` in a new terminal.
- On Windows, add `%USERPROFILE%\\.blocks\\bin` to the user PATH.
- On macOS/Linux, reload the shell profile after installation.

### Registration or publishing says the agent name is taken

Agent names are claimed network-wide, not just within an organization. Choose a more specific name containing only letters, digits, and underscores.

### Authentication fails

- Run `blocks login --write-env` again and select the correct organization.
- Confirm `BLOCKS_API_KEY` is present only in the native project’s environment.
- If the key is expired or revoked, create a fresh key and restart `blocks run`.
- If a key leaked, disable it in the dashboard; `blocks logout` alone does not revoke it.

### The agent runs but does not receive tasks

- Confirm `blocks run` is still running.
- Confirm the handler returns the required `artifacts` structure.
- Confirm the caller’s `partId` is exactly `request`.
- Check whether the agent is private and whether the caller has an active invitation.

### Local imports fail

Run local handlers through the package-aware commands from the repository root:

```bash
python -m blocks_agents.handlers
```

Do not execute a handler file directly if it uses package-relative imports.

### Forecasting returns `FAIL`

This is intentional. The project currently has embedded provenance rows and insufficient dated history for validated production forecasting. Resolve source identity, add dated observations, define independently observed future outcomes, and implement chronological evaluation before relaxing the gate.

## 19. Node.js gateway: one instance for all agents

`crypto_yield_matrix_node_gateway/` is a Node.js consumer project that serves all 12 published agents from a single process. It was generated with the official Blocks CLI (`blocks init crypto_yield_matrix_node_gateway --mode consumer --language node --yes`) and extended with a small HTTP gateway that shares one `TaskClient` across every agent.

### Endpoints

- `GET /health` — liveness and fleet summary.
- `GET /agents` — lists the 12 served agents with descriptions.
- `POST /agents/:agentName/invoke` — forwards a JSON request to one published agent and returns its terminal state, progress, and artifacts.

The request body is passed through verbatim as the `request` part, so handler-specific fields (`question`, `symbol`, `category`, `source_file`, `features`, `target`, `split`, ...) work unchanged. Because every published agent is paid ($0.10/task), the shared client uses `billingMode: 'paid'`. The API key stays server-side in the ignored `.env` and is never returned by any endpoint.

### Run it

```bash
cd crypto_yield_matrix_node_gateway
npm install
blocks login --write-env   # writes BLOCKS_API_KEY to the ignored .env
npm start                  # http://localhost:3000
```

Environment variables: `GATEWAY_PORT` (default 3000), `GATEWAY_TASK_TIMEOUT_MS` (default 120000), `GATEWAY_MAX_BODY_BYTES` (default 1000000), and `GATEWAY_MAX_CONCURRENT_TASKS` (default 8). The concurrency cap is deliberate: every accepted invocation is paid, so excess requests receive HTTP 503 with `Retry-After: 5` instead of creating an unbounded billable backlog.

Example invocation:

```bash
curl -s localhost:3000/agents/crypto_risk_analyst/invoke \
  -H 'content-type: application/json' \
  -d '{"question":"Compare BTC yield and downside context","symbol":"BTC","source_file":"yield_data.csv"}'
```

### Validate without spending

```bash
npm run check   # tsc --noEmit
npm run smoke   # routing/validation only — never dispatches a paid task
```

The smoke test uses a placeholder key and exercises only health, listing, unknown-agent 404s, malformed-body 400s, required-question validation, and idempotency-header validation; it never calls a real agent.

The gateway process is also managed by [`Restart-BlocksAgents.ps1`](Restart-BlocksAgents.ps1): it starts `node --import tsx index.ts` from this directory (state entry `gateway`, logs under `blocks-agent-logs/gateway/`). Use `-AgentName gateway` to manage only the gateway or `-SkipGateway` to leave it out of fleet restarts. The gateway reads `BLOCKS_API_KEY` from its ignored `.env` and honors `GATEWAY_PORT` from its environment or `.env`.

## 20. Official references

- [Blocks docs home](https://blocks.ai/docs)
- [Blocks Quickstart](https://blocks.ai/docs/quickstart)
- [Blocks key concepts](https://blocks.ai/docs/key-concepts)
- [Blocks authentication reference](https://blocks.ai/docs/authentication)
- [Blocks Network catalog](https://app.blocks.ai)
- [Project agent index](blocks_agents/agent_cards.json)
- [Project agent README](blocks_agents/README.md)
- [Project validation report](validate.md)
