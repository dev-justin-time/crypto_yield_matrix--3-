/**
 * Gateway smoke test.
 *
 * Exercises routing and request validation only. It never dispatches a real
 * task (a paid $0.10 call), so it works with a placeholder API key.
 *
 *   npm run smoke
 */
import { createGateway } from './server.js';
import { AGENTS } from './agents.js';

const DUMMY_KEY = 'sk_test_placeholder_for_smoke_only';

async function expectStatus(url: string, init: RequestInit, expected: number): Promise<void> {
  const res = await fetch(url, init);
  const body = await res.text();
  if (res.status !== expected) {
    throw new Error(`expected ${expected} for ${init.method ?? 'GET'} ${url}, got ${res.status}: ${body}`);
  }
  return;
}

async function main(): Promise<void> {
  const gateway = createGateway({ apiKey: DUMMY_KEY, taskTimeoutMs: 5_000 });
  await new Promise<void>((resolve) => gateway.server.listen(0, resolve));
  const address = gateway.server.address();
  if (address === null || typeof address === 'string') {
    throw new Error('expected an ephemeral TCP port');
  }
  const base = `http://127.0.0.1:${address.port}`;

  // Liveness endpoint.
  await expectStatus(`${base}/health`, { method: 'GET' }, 200);

  // Fleet listing: exactly the 12 published agents.
  const agentsRes = await fetch(`${base}/agents`);
  const agentsBody = (await agentsRes.json()) as { agents: unknown[] };
  if (agentsRes.status !== 200 || agentsBody.agents.length !== 12) {
    throw new Error(`expected 12 agents, got ${agentsBody.agents.length}`);
  }

  // Unknown agent -> 404 (rejected before any SDK client work).
  await expectStatus(
    `${base}/agents/not_an_agent/invoke`,
    { method: 'POST', body: '{}', headers: { 'content-type': 'application/json' } },
    404,
  );

  // Invalid JSON -> 400.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: 'not json', headers: { 'content-type': 'application/json' } },
    400,
  );

  // Non-object JSON (array) -> 400.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: '[]', headers: { 'content-type': 'application/json' } },
    400,
  );

  // Missing required question -> 400 before any paid dispatch.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: '{}', headers: { 'content-type': 'application/json' } },
    400,
  );

  // Invalid idempotency-key header -> 400 before any paid dispatch.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    {
      method: 'POST',
      body: JSON.stringify({ question: 'test' }),
      headers: { 'content-type': 'application/json', 'x-idempotency-key': 'x'.repeat(201) },
    },
    400,
  );

  // Unknown route -> 404.
  await expectStatus(`${base}/nope`, { method: 'GET' }, 404);

  console.log(`smoke: PASS (health, ${agentsBody.agents.length} agents, validation)`);
  await gateway.destroy();
  await new Promise<void>((resolve) => gateway.server.close(() => resolve()));
}

main().catch((err) => {
  console.error('smoke: FAIL', err);
  process.exit(1);
});
