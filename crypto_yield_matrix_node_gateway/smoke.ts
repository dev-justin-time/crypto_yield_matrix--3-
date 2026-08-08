/**
 * Gateway smoke test.
 *
 * Exercises routing and request validation only. It never dispatches a real
 * task (a paid $0.10 call), so it works with placeholder credentials.
 *
 *   npm run smoke
 */
import { createGateway, parseClientAgents, parseClientKeys } from './server.js';
import { AGENTS } from './agents.js';

const DUMMY_KEY = 'sk_test_placeholder_for_smoke_only';
const CLIENT_SECRET = 'client_secret_placeholder_12345';

async function expectStatus(url: string, init: RequestInit, expected: number): Promise<Response> {
  const res = await fetch(url, init);
  const body = await res.text();
  if (res.status !== expected) {
    throw new Error(`expected ${expected} for ${init.method ?? 'GET'} ${url}, got ${res.status}: ${body}`);
  }
  return res;
}

function fakeTaskClient(): any {
  return {
    destroy() {},
    sendMessage: async () => {
      throw new Error('fake client must never dispatch a paid task');
    },
  };
}

async function main(): Promise<void> {
  if (parseClientKeys(`smoke=${CLIENT_SECRET}`).smoke !== CLIENT_SECRET) {
    throw new Error('client key parser failed');
  }
  if (!parseClientAgents('smoke=crypto_risk_analyst').smoke?.has('crypto_risk_analyst')) {
    throw new Error('client agent parser failed');
  }
  if (parseClientAgents('unknown=crypto_risk_analyst').unknown === undefined) {
    throw new Error('client agent parser should parse names before startup cross-check');
  }
  const gateway = createGateway({
    apiKey: DUMMY_KEY,
    clientKeys: { smoke: CLIENT_SECRET },
    clientAgents: { smoke: new Set(['crypto_risk_analyst']) },
    taskTimeoutMs: 5_000,
    budgetStateFile: '',
    maxRequestsPerMinute: 2,
    maxDailyTasks: 1,
    maxDailySpendUsd: 0.10,
    taskCostUsd: 0.10,
    taskClientFactory: async () => fakeTaskClient(),
  });
  await new Promise<void>((resolve) => gateway.server.listen(0, resolve));
  const address = gateway.server.address();
  if (address === null || typeof address === 'string') {
    throw new Error('expected an ephemeral TCP port');
  }
  const base = `http://127.0.0.1:${address.port}`;
  const invokeHeaders = {
    'content-type': 'application/json',
    authorization: `Bearer ${CLIENT_SECRET}`,
  };

  // Liveness/readiness are no-spend endpoints.
  await expectStatus(`${base}/health`, { method: 'GET' }, 200);
  await expectStatus(`${base}/ready`, { method: 'GET' }, 200);

  // Fleet listing: exactly the 12 published agents.
  const agentsRes = await fetch(`${base}/agents`);
  const agentsBody = (await agentsRes.json()) as { agents: unknown[] };
  if (agentsRes.status !== 200 || agentsBody.agents.length !== 12) {
    throw new Error(`expected 12 agents, got ${agentsBody.agents.length}`);
  }

  // Missing gateway credentials -> 401 before any paid dispatch.
  const unauthorized = await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: JSON.stringify({ question: 'test' }), headers: { 'content-type': 'application/json' } },
    401,
  );
  if (!unauthorized.headers.get('x-request-id')) throw new Error('401 response missing request id');

  // Unknown agent -> 404 (rejected before any SDK client work).
  await expectStatus(
    `${base}/agents/not_an_agent/invoke`,
    { method: 'POST', body: '{}', headers: invokeHeaders },
    404,
  );

  // Invalid JSON -> 400.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: 'not json', headers: invokeHeaders },
    400,
  );

  // Non-object JSON (array) -> 400.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: '[]', headers: invokeHeaders },
    400,
  );

  // Missing required question -> 400 before any paid dispatch.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: '{}', headers: invokeHeaders },
    400,
  );

  // Invalid source file -> 400 before any paid dispatch.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: JSON.stringify({ question: 'test', source_file: 'yield_data1.csv' }), headers: invokeHeaders },
    400,
  );

  // Invalid content type -> 415 before any paid dispatch.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: JSON.stringify({ question: 'test' }), headers: { ...invokeHeaders, 'content-type': 'text/plain' } },
    415,
  );

  // Invalid idempotency-key header -> 400 before any paid dispatch.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    {
      method: 'POST',
      body: JSON.stringify({ question: 'test' }),
      headers: { ...invokeHeaders, 'x-idempotency-key': 'x'.repeat(201) },
    },
    400,
  );

  // A valid-shaped request reaches the fake client and is rejected with 500;
  // its reservation is retained conservatively, so the next request is 429.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: JSON.stringify({ question: 'test' }), headers: invokeHeaders },
    500,
  );
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: JSON.stringify({ question: 'test again' }), headers: invokeHeaders },
    429,
  );

  // Unknown route -> 404.
  await expectStatus(`${base}/nope`, { method: 'GET' }, 404);

  console.log(`smoke: PASS (auth, readiness, budget, health, ${agentsBody.agents.length} agents, validation; no paid dispatch)`);
  await gateway.destroy();
  await new Promise<void>((resolve) => gateway.server.close(() => resolve()));
}

main().catch((err) => {
  console.error('smoke: FAIL', err);
  process.exit(1);
});
