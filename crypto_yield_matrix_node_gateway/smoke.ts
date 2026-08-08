/**
 * Gateway smoke test.
 *
 * Exercises routing and request validation only. It never dispatches a real
 * task (a paid $0.10 call), so it works with placeholder credentials.
 *
 *   npm run smoke
 */
import { unlinkSync, writeFileSync } from 'node:fs';
import { createGateway, isLoopbackHost, parseClientAgents, parseClientKeys } from './server.js';
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
  if (!isLoopbackHost('127.0.0.1') || !isLoopbackHost('localhost') || isLoopbackHost('192.0.2.1')) {
    throw new Error('host binding policy parser failed');
  }
  if (parseClientKeys(`smoke=${CLIENT_SECRET}`).smoke !== CLIENT_SECRET) {
    throw new Error('client key parser failed');
  }
  if (!parseClientAgents('smoke=crypto_risk_analyst').smoke?.has('crypto_risk_analyst')) {
    throw new Error('client agent parser failed');
  }
  if (parseClientAgents('unknown=crypto_risk_analyst').unknown === undefined) {
    throw new Error('client agent parser should parse names before startup cross-check');
  }
  const killSwitchFile = `.smoke-kill-switch-${process.pid}`;
  const gateway = createGateway({
    apiKey: DUMMY_KEY,
    clientKeys: { smoke: CLIENT_SECRET },
    clientAgents: { smoke: new Set(['crypto_risk_analyst']) },
    taskTimeoutMs: 5_000,
    budgetStateFile: '',
    killSwitchFile,
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
  const ready = await expectStatus(`${base}/ready`, { method: 'GET' }, 200);
  if (!ready.headers.get('x-gateway-remaining-tasks') || !ready.headers.get('x-gateway-remaining-spend-usd')) {
    throw new Error('readiness response missing remaining-budget headers');
  }

  // Fleet listing: exactly the 12 published agents.
  const metricsBeforeUnauthorized = await fetch(`${base}/metrics`);
  if (metricsBeforeUnauthorized.status !== 401) {
    throw new Error(`expected 401 for unauthenticated GET ${base}/metrics, got ${metricsBeforeUnauthorized.status}`);
  }
  const metricsBefore = await fetch(`${base}/metrics`, { headers: { authorization: `Bearer ${CLIENT_SECRET}` } });
  if (metricsBefore.status !== 200) {
    throw new Error(`expected 200 for authenticated GET ${base}/metrics, got ${metricsBefore.status}: ${await metricsBefore.text()}`);
  }
  const metricsBody = (await metricsBefore.json()) as { requestsTotal: number; billingMode: string };
  if (metricsBody.billingMode !== 'paid' || metricsBody.requestsTotal < 1) {
    throw new Error('metrics endpoint did not expose safe request/billing counters');
  }
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

  // Unsupported request schema -> 400 before any paid dispatch.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: JSON.stringify({ question: 'test' }), headers: { ...invokeHeaders, 'x-gateway-schema-version': '999' } },
    400,
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
  // The budget rejection still consumed the client request window; the next
  // request is rejected specifically by the rolling rate limit.
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: JSON.stringify({ question: 'rate limited' }), headers: invokeHeaders },
    429,
  );

  // A file-based emergency stop changes readiness and blocks paid dispatch.
  writeFileSync(killSwitchFile, 'pause');
  await expectStatus(`${base}/ready`, { method: 'GET' }, 503);
  await expectStatus(
    `${base}/agents/crypto_risk_analyst/invoke`,
    { method: 'POST', body: JSON.stringify({ question: 'paused task' }), headers: invokeHeaders },
    503,
  );
  unlinkSync(killSwitchFile);

  // Unknown route -> 404.
  await expectStatus(`${base}/nope`, { method: 'GET' }, 404);

  const metricsAfter = await fetch(`${base}/metrics`, { headers: { authorization: `Bearer ${CLIENT_SECRET}` } });
  if (metricsAfter.status !== 200) {
    throw new Error(`expected 200 for authenticated GET ${base}/metrics, got ${metricsAfter.status}: ${await metricsAfter.text()}`);
  }
  const finalMetrics = (await metricsAfter.json()) as { authRejected: number; budgetRejected: number; rateLimitRejected: number; killSwitchRejected: number; responsesByStatus: Record<string, number> };
  if (finalMetrics.authRejected < 1 || finalMetrics.budgetRejected < 1 || finalMetrics.rateLimitRejected < 1 || finalMetrics.killSwitchRejected < 1 || !finalMetrics.responsesByStatus['400']) {
    throw new Error('metrics endpoint did not record smoke-test outcomes');
  }
  console.log(`smoke: PASS (auth, readiness, protected metrics, budget, health, ${agentsBody.agents.length} agents, validation; no paid dispatch)`);
  try { unlinkSync(killSwitchFile); } catch {}
  await gateway.destroy();
  await new Promise<void>((resolve) => gateway.server.close(() => resolve()));
}

main().catch((err) => {
  console.error('smoke: FAIL', err);
  process.exit(1);
});
