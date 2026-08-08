/**
 * No-spend resilience checks for the gateway.
 * Uses a fake client that never accepts a task; no Blocks SDK or network call.
 *
 *   npm run resilience
 */
import { createGateway } from './server.js';

const API_KEY = 'sk_test_resilience_placeholder';
const CLIENT_SECRET = 'resilience_client_secret_12345';

function neverAcceptingClient(accepted: { resolve: () => void }): any {
  return {
    destroy() {},
    sendMessage: () => {
      accepted.resolve();
      return new Promise(() => undefined);
    },
  };
}

async function main(): Promise<void> {
  let firstSend!: () => void;
  const firstSendStarted = new Promise<void>((resolve) => { firstSend = resolve; });
  const gateway = createGateway({
    apiKey: API_KEY,
    clientKeys: { resilience: CLIENT_SECRET },
    taskTimeoutMs: 100,
    maxConcurrentTasks: 1,
    maxRequestsPerMinute: 20,
    maxDailyTasks: 10,
    maxDailySpendUsd: 1,
    taskCostUsd: 0.10,
    budgetStateFile: '',
    taskClientFactory: async () => neverAcceptingClient({ resolve: firstSend }),
  });
  await new Promise<void>((resolve) => gateway.server.listen(0, '127.0.0.1', resolve));
  const address = gateway.server.address();
  if (!address || typeof address === 'string') throw new Error('resilience server did not bind to a TCP port');
  const base = `http://127.0.0.1:${address.port}`;
  const url = `${base}/agents/crypto_risk_analyst/invoke`;
  const init: RequestInit = {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${CLIENT_SECRET}`,
    },
    body: JSON.stringify({ question: 'no-spend timeout test' }),
  };

  const first = fetch(url, init);
  await firstSendStarted;
  const saturated = await fetch(url, init);
  if (saturated.status !== 503) {
    throw new Error(`expected 503 during capacity saturation, got ${saturated.status}`);
  }
  const timedOut = await first;
  if (timedOut.status !== 504) {
    throw new Error(`expected 504 after fake provider timeout, got ${timedOut.status}`);
  }
  const metrics = await fetch(`${base}/metrics`, {
    headers: { authorization: `Bearer ${CLIENT_SECRET}` },
  });
  const metricsBody = await metrics.json() as { capacityRejected: number; taskTimeouts: number };
  if (metricsBody.capacityRejected < 1 || metricsBody.taskTimeouts < 1) {
    throw new Error('resilience metrics did not record capacity and timeout outcomes');
  }
  await gateway.destroy();
  await new Promise<void>((resolve) => gateway.server.close(() => resolve()));

  let downloadCalled = false;
  const artifactGateway = createGateway({
    apiKey: API_KEY,
    clientKeys: { resilience: CLIENT_SECRET },
    taskTimeoutMs: 500,
    maxArtifactBytes: 10,
    budgetStateFile: '',
    taskClientFactory: async () => ({
      destroy() {},
      sendMessage: async () => ({
        taskId: 'fake-artifact-task',
        onProgress() {},
        waitForTerminal: async () => ({ state: 'completed' }),
        listArtifacts: () => [{ kind: 'file', fileName: 'too-large.json', mimeType: 'application/json', size: 100 }],
        downloadArtifact: async () => { downloadCalled = true; throw new Error('download must not be called'); },
        close() {},
      }),
    } as any),
  });
  await new Promise<void>((resolve) => artifactGateway.server.listen(0, '127.0.0.1', resolve));
  const artifactAddress = artifactGateway.server.address();
  if (!artifactAddress || typeof artifactAddress === 'string') throw new Error('artifact test server did not bind');
  const artifactResponse = await fetch(`http://127.0.0.1:${artifactAddress.port}/agents/crypto_risk_analyst/invoke`, {
    ...init,
    body: JSON.stringify({ question: 'declared artifact limit test' }),
  });
  const artifactBody = await artifactResponse.json() as { artifactStatus?: string; error?: string };
  if (artifactResponse.status !== 502 || artifactBody.artifactStatus !== 'partial' || downloadCalled) {
    throw new Error('declared oversized artifact was not rejected before download');
  }
  await artifactGateway.destroy();
  await new Promise<void>((resolve) => artifactGateway.server.close(() => resolve()));
  console.log('resilience: PASS (no-spend capacity, timeout, metrics, and artifact cap)');
}

main().catch((error) => {
  console.error('resilience: FAIL', error);
  process.exit(1);
});
