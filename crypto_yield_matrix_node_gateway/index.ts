/**
 * crypto_yield_matrix_node_gateway — single Node.js instance serving all 12
 * published Blocks agents through one shared TaskClient.
 *
 *   npm install
 *   blocks login --write-env        # writes BLOCKS_API_KEY to .env
 *   npm start
 *
 * Endpoints:
 *   GET  /health
 *   GET  /agents
 *   POST /agents/:agentName/invoke  (body: JSON research request)
 */
import 'dotenv/config';
import { createGateway } from './server.js';
import { AGENTS } from './agents.js';

const apiKey = process.env.BLOCKS_API_KEY;
if (!apiKey) {
  console.error(
    "BLOCKS_API_KEY is not set. Run 'blocks login --write-env' in this project or set it in .env before starting.",
  );
  process.exit(1);
}

function positiveIntegerEnv(name: string, fallback: number): number {
  const value = Number(process.env[name] ?? fallback);
  if (!Number.isInteger(value) || value < 1) {
    console.error(`[gateway] invalid ${name} '${process.env[name] ?? ''}'`);
    process.exit(1);
  }
  return value;
}

const port = Number(process.env.GATEWAY_PORT ?? 3000);
if (!Number.isInteger(port) || port < 0 || port > 65_535) {
  console.error(`[gateway] invalid GATEWAY_PORT '${process.env.GATEWAY_PORT ?? ''}'`);
  process.exit(1);
}

const taskTimeoutMs = positiveIntegerEnv('GATEWAY_TASK_TIMEOUT_MS', 120_000);
const maxBodyBytes = positiveIntegerEnv('GATEWAY_MAX_BODY_BYTES', 1_000_000);
const maxConcurrentTasks = positiveIntegerEnv('GATEWAY_MAX_CONCURRENT_TASKS', 8);

const gateway = createGateway({
  apiKey,
  taskTimeoutMs,
  maxBodyBytes,
  maxConcurrentTasks,
});

gateway.server.listen(port, () => {
  console.log(`[gateway] listening on http://localhost:${port}`);
  console.log(`[gateway] serving ${AGENTS.length} agents (billing: paid, $0.10/task)`);
});

let shuttingDown = false;
function shutdown(signal: NodeJS.Signals): void {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`[gateway] ${signal} received; draining connections...`);
  gateway.server.close(() => {
    void gateway.destroy().finally(() => process.exit(0));
  });
  // server.close() only stops accepting new connections; close idle keep-alive
  // connections so the drain completes promptly on a quiet gateway.
  if (typeof gateway.server.closeIdleConnections === 'function') {
    gateway.server.closeIdleConnections();
  }
  // Last resort: force-close remaining connections and exit cleanly.
  setTimeout(() => {
    console.error('[gateway] drain timed out; closing remaining connections');
    gateway.server.closeAllConnections?.();
    void gateway.destroy().finally(() => process.exit(0));
  }, 10_000).unref();
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
