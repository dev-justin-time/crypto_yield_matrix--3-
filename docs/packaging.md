# Deterministic Blocks packaging

This repository now has a reproducible packaging path for the local scaffold and
native Blocks deployment projects.

## Source of truth

- Root agent cards: `blocks_agents/*.json` and `blocks_agents/agent_cards.json`.
- Root business handlers: `blocks_agents/handlers/*.py`.
- Canonical data and generated evidence exports are mirrored from the repository
  root; live snapshots and credentials are intentionally excluded.
- The A2A orchestrator remains a hand-maintained custom adapter because it
  dispatches private specialist tasks and has different runtime behavior.

## Local commands

```bash
# Generate thin native adapters and deployment metadata from root cards.
python generate_deployments.py --write

# Copy approved source mirrors and write the SHA-256 manifest.
python sync_deployments.py --write

# CI-style checks; neither command calls the network or Blocks.
python generate_deployments.py --check
python sync_deployments.py --check

# Scaffold and one materialized deployment package; standard library only.
python test_packaging.py
```

`deployment_mirror_manifest.json` records every mirrored source file, target,
and SHA-256 digest. A mismatch is a hard failure. Run the checks before
materializing or publishing any package.

## Native adapter generation

Standard specialist `handler.py` files are generated as transport-only wrappers
that import the matching root handler. `deployment-metadata.json` records the
source card hash, stable card contract, native card hash, generated adapter type,
and the required external `blocks check` gate. The generator validates identity,
description, provider, task kinds, tags, and the native `./handler.py:handler`
entrypoint. It does not overwrite the custom A2A orchestrator and does not run
`blocks check`, registration, publishing, or paid tasks. All native Python projects pin `blocks-network==1.0.11`, and the Node gateway pins `@blocks-network/sdk` to `1.0.11`; upgrades require deliberate no-spend validation and a private canary.

## Guarded private trigger

Use the trigger utility for explicit no-spend validation:

```bash
python trigger_guarded.py --agent crypto_risk_analyst --dry-run
```

The default path prints `not dispatched` and never imports the Blocks SDK. A real private trigger explicitly creates the Python SDK client with `billing_mode="paid"` and exits nonzero for failed, canceled, or timed-out terminal states. It requires all of the following explicit choices:

```bash
python trigger_guarded.py \
  --agent crypto_risk_analyst \
  --live \
  --confirm-paid \
  --request '{"question":"Analyze BTC","symbol":"BTC","source_file":"yield_data.csv"}'
```

This may incur a paid task. It requires `BLOCKS_API_KEY`, an installed
`blocks-network` package, a valid private registration, and accepted A2A
permissions where applicable. It performs no automatic retry and does not
claim that a canary passed unless the operator observes the terminal result.

## Required external rollout sequence

1. Build/check deterministic packages locally with no credentials.
2. In each native package's environment, run `blocks check` with the official
   CLI; record the output and package revision.
3. Register privately and confirm provider connectivity.
4. Verify the orchestrator identity can reach every required private specialist.
5. Run one budgeted paid canary per changed package using the guarded trigger;
   record task ID, terminal state, artifact schema, latency, and spend.
6. Compare artifacts against the pre-change baseline, including partial A2A
   failures and downloadable artifacts.
7. Compare package size and startup time before/after any pruning; do not prune
   specialist modules until imports and cards still resolve.

No local command in this repository can prove live registration, billing,
provider connectivity, A2A permissions, artifact downloads, or production
startup performance. Those remain release evidence, not generated claims.

## Missing numeric values

Artifacts now include a `data_quality` policy and serialize unavailable numeric
fields as JSON `null`. A supplied numeric zero remains zero. Missing, blank,
invalid, NaN, and infinite values are never silently converted to zero. Derived
ratios remain `null` when a numerator or denominator is unavailable or a
 denominator is zero.
