# Production Incident Runbook

This runbook is for the accountable operator of the Crypto Yield Matrix gateway and Blocks fleet. It is intentionally operational: it does not authorize registration, publishing, credential rotation, or paid tasks by itself.

## Emergency stop

1. Create the configured gateway pause file (`GATEWAY_KILL_SWITCH_FILE`, normally `.gateway-state/PAUSE_PAID_TASKS`).
2. Confirm `/ready` reports HTTP 503 and `kill_switch_active`.
3. Confirm new `/agents/*/invoke` requests return HTTP 503.
4. Preserve request IDs, logs, task IDs, and the budget snapshot; do not retry uncertain paid requests blindly.
5. If the provider fleet must also stop, use the supervised platform's stop/scale-to-zero procedure.
6. Record who stopped service, UTC time, reason, and the restart approver.

## Spend or duplicate-task anomaly

- Pause new dispatches immediately.
- Compare gateway budget state, request IDs, idempotency keys, Blocks task IDs, and billing records.
- Treat uncertain sends as potentially billable until Blocks confirms otherwise.
- Do not remove budget reservations to make the ledger look correct.
- Escalate before resuming service; document the approved new ceiling.

## Gateway outage or unhealthy readiness

- Check `/health`, `/ready`, authenticated `/metrics`, and `/metrics/prometheus` from the internal network.
- Check container/service restart history, memory/CPU limits, disk space for the budget volume, and upstream Blocks connectivity.
- Preserve the release ID/image digest before rollback.
- Roll back to the last approved image only after confirming the budget ledger is preserved and the external edge points to the approved instance.

## Credential incident

- Revoke the affected Blocks or gateway credential in the secret manager/provider control plane.
- Inject the replacement through the secret manager; never paste it into logs, chat, source, or an image layer.
- Test old-key rejection and new-key authentication from the internal operator path.
- Review access logs and rotate any dependent credentials.
- Record the incident owner, UTC timestamps, affected scope, and recovery result.

## A2A or provider degradation

- Keep the public gateway stopped or paused if outputs cannot be traced to the expected agent/version.
- Capture provider health, registry version, A2A grant state, terminal states, and artifact status.
- Return partial/failed research clearly; do not convert missing specialist evidence into a successful conclusion.
- Resume only after an accountable operator approves the evidence and canary plan.

## Rollback procedure

1. Identify the last known-good release: check `release_record.json` and the deployed image digest in the container platform.
2. Stop new paid dispatches: create the kill-switch file or scale the gateway to zero.
3. Verify the budget ledger (`gateway-budget` volume) is preserved before rollback.
4. Deploy the previous approved image digest and confirm `/ready` returns 200.
5. Remove the kill-switch file and verify a controlled test request completes.
6. Record the rollback reason, UTC timestamps, before/after image digests, and approver.

## Required evidence after recovery

- Incident timeline and owner.
- Release/image digest and rollback result.
- Gateway and provider health window.
- Request/task IDs and billing reconciliation where paid tasks were involved.
- Monitoring alerts, acknowledged actions, and remaining follow-up work.
