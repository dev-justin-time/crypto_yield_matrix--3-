/**
 * Single-instance gateway for all 12 published Blocks agents.
 *
 * One Node.js process owns a single shared `TaskClient` and exposes a small
 * HTTP API:
 *
 *   GET  /health                  -> liveness + fleet summary
 *   GET  /agents                  -> list of served agents
 *   POST /agents/:name/invoke     -> dispatch a JSON task to one agent
 *
 * The request body is forwarded verbatim to the agent's `request` part, so
 * handler-specific fields (question, symbol, category, source_file, ...)
 * pass through unchanged.
 */
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { TaskClient, textPart } from '@blocks-network/sdk';
import type {
  ArtifactRef,
  ProgressEvent,
  TaskSession,
  TerminalEvent,
} from '@blocks-network/sdk';
import { AGENTS, getAgent } from './agents.js';

/**
 * All agents in this fleet are published with paid billing at $0.10/task,
 * so the shared client must use 'paid' or the backend rejects the task.
 */
const BILLING_MODE = 'paid' as const;

export interface GatewayOptions {
  apiKey: string;
  taskTimeoutMs?: number;
  maxBodyBytes?: number;
  maxProgressEvents?: number;
  /** Maximum number of paid tasks this gateway will have in flight. */
  maxConcurrentTasks?: number;
}

export interface Gateway {
  server: ReturnType<typeof createServer>;
  /** Destroy the shared SDK client. Safe to call once (e.g. on shutdown). */
  destroy(): Promise<void>;
}

class HttpError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

/** Reject with an HttpError if the wrapped promise does not settle in time. */
function withDeadline<T>(promise: Promise<T>, ms: number, message: string): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new HttpError(504, message)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => {
    if (timer) clearTimeout(timer);
  });
}

async function readJsonBody(req: IncomingMessage, maxBodyBytes: number): Promise<unknown> {
  let size = 0;
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > maxBodyBytes) {
      throw new HttpError(413, `request body exceeds ${maxBodyBytes} bytes`);
    }
    chunks.push(chunk as Buffer);
  }
  if (chunks.length === 0) {
    return {};
  }
  const raw = Buffer.concat(chunks).toString('utf8');
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    throw new HttpError(400, 'request body must be valid JSON');
  }
}

/**
 * Discard an unread request body (capped) so keep-alive connections are not
 * desynced when a route responds without consuming its payload.
 */
async function drainRequest(req: IncomingMessage, maxBytes: number): Promise<void> {
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > maxBytes) {
      req.destroy();
      return;
    }
  }
}

function tryParseJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function sendTaskWithDeadline(
  client: TaskClient,
  agentName: string,
  payload: Record<string, unknown>,
  taskTimeoutMs: number,
  idempotencyKey?: string,
): Promise<TaskSession> {
  let timedOut = false;
  const sendPromise = client.sendMessage({
    agentName,
    requestParts: [textPart(JSON.stringify(payload), 'request')],
    ...(idempotencyKey ? { idempotencyKey } : {}),
  });
  // A SendMessage RPC can resolve after our local deadline. Attach a handler
  // now so a late accepted paid task is canceled instead of orphaned.
  void sendPromise.then((lateSession) => {
    if (timedOut) {
      void lateSession.cancel().catch(() => undefined);
      lateSession.close();
    }
  }).catch(() => undefined);
  try {
    return await withDeadline(
      sendPromise,
      taskTimeoutMs,
      `agent '${agentName}' did not accept the task within ${taskTimeoutMs} ms`,
    );
  } catch (error) {
    timedOut = true;
    throw error;
  }
}

async function downloadArtifacts(session: TaskSession, taskTimeoutMs: number): Promise<unknown[]> {
  const refs: ArtifactRef[] = session.listArtifacts();
  const downloadTimeoutMs = Math.min(30_000, taskTimeoutMs);
  const out: unknown[] = [];
  for (const ref of refs) {
    try {
      const downloaded = await withDeadline(
        session.downloadArtifact(ref),
        downloadTimeoutMs,
        'artifact download timed out',
      );
      const text = new TextDecoder().decode(downloaded.data);
      const mimeType = downloaded.mimeType || ref.mimeType || '';
      const isJson = mimeType.includes('json') || /^[{[]/.test(text.trim());
      out.push({
        fileName: ref.fileName ?? downloaded.fileName ?? null,
        mimeType,
        size: downloaded.data.byteLength,
        data: isJson ? tryParseJson(text) : text,
      });
    } catch (err) {
      out.push({
        fileName: ref.fileName ?? null,
        mimeType: ref.mimeType ?? '',
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
  return out;
}

interface InvokeResult {
  agent: string;
  taskId: string;
  state: 'completed' | 'failed' | 'canceled' | 'error';
  durationMs: number;
  progress: string[];
  artifacts?: unknown[];
  reason?: string;
  error?: string;
}

async function invokeAgent(
  client: TaskClient,
  agentName: string,
  payload: Record<string, unknown>,
  taskTimeoutMs: number,
  maxProgressEvents: number,
  idempotencyKey?: string,
): Promise<InvokeResult> {
  const session = await sendTaskWithDeadline(
    client,
    agentName,
    payload,
    taskTimeoutMs,
    idempotencyKey,
  );

  const progress: string[] = [];
  session.onProgress((event: ProgressEvent) => {
    const text = event.message ?? event.progress ?? '';
    if (text !== '' && progress.length < maxProgressEvents) {
      progress.push(String(text));
    }
  });

  const startedAt = Date.now();
  let terminal: TerminalEvent;
  try {
    terminal = await session.waitForTerminal(taskTimeoutMs);
  } catch {
    // A local timeout does not stop a remote paid task. Ask Blocks to cancel
    // it before closing the session; cancellation is best-effort because the
    // task may already have reached a terminal state.
    await session.cancel().catch(() => undefined);
    session.close();
    throw new HttpError(504, `task did not reach a terminal state within ${taskTimeoutMs} ms`);
  }

  const result: InvokeResult = {
    agent: agentName,
    taskId: session.taskId,
    state: terminal.state,
    durationMs: Date.now() - startedAt,
    progress,
  };

  try {
    if (terminal.state === 'completed') {
      result.artifacts = await downloadArtifacts(session, taskTimeoutMs);
    } else if (terminal.reason !== undefined) {
      result.reason = terminal.reason;
    } else if (terminal.error !== undefined) {
      result.error = terminal.error;
    }
  } finally {
    session.close();
  }
  return result;
}

export function createGateway(options: GatewayOptions): Gateway {
  const taskTimeoutMs = options.taskTimeoutMs ?? 120_000;
  const maxBodyBytes = options.maxBodyBytes ?? 1_000_000;
  const maxProgressEvents = options.maxProgressEvents ?? 50;
  const maxConcurrentTasks = options.maxConcurrentTasks ?? 8;
  if (!Number.isInteger(maxConcurrentTasks) || maxConcurrentTasks < 1) {
    throw new Error('maxConcurrentTasks must be a positive integer');
  }

  let inFlightTasks = 0;
  let clientPromise: Promise<TaskClient> | null = null;
  let clientReady = false;
  const getClient = async (): Promise<TaskClient> => {
    if (!clientPromise) {
      clientPromise = TaskClient.create({
        billingMode: BILLING_MODE,
        apiKey: options.apiKey,
      });
      try {
        await clientPromise;
        clientReady = true;
      } catch (error) {
        clientPromise = null;
        throw error;
      }
    }
    return clientPromise;
  };

  const destroy = async (): Promise<void> => {
    if (clientPromise) {
      const client = await clientPromise.catch(() => null);
      client?.destroy();
      clientPromise = null;
    }
  };

  const server = createServer((req: IncomingMessage, res: ServerResponse) => {
    void (async () => {
      try {
        const url = new URL(req.url ?? '/', 'http://localhost');
        const { pathname } = url;

        if (req.method === 'GET' && pathname === '/health') {
          sendJson(res, 200, {
            status: 'ok',
            uptimeSeconds: Math.round(process.uptime()),
            agents: AGENTS.length,
            billingMode: BILLING_MODE,
            clientReady,
            inFlightTasks,
            maxConcurrentTasks,
          });
          return;
        }

        if (req.method === 'GET' && pathname === '/agents') {
          sendJson(res, 200, { agents: AGENTS });
          return;
        }

        const invokeMatch = pathname.match(/^\/agents\/([A-Za-z0-9_]+)\/invoke$/);
        if (req.method === 'POST' && invokeMatch) {
          const agentName = invokeMatch[1];
          // Always consume the request body before any early exit so the
          // keep-alive connection stays in sync for the next request.
          const payload = await readJsonBody(req, maxBodyBytes);
          if (!getAgent(agentName)) {
            throw new HttpError(404, `unknown agent '${agentName}'`);
          }
          // Validate the request shape before any SDK client work so bad
          // input is rejected locally instead of being sent to the agent.
          if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
            throw new HttpError(400, 'request body must be a JSON object');
          }
          const request = payload as Record<string, unknown>;
          if (typeof request.question !== 'string' || request.question.trim() === '') {
            throw new HttpError(400, 'request body requires a non-empty string question');
          }
          if (inFlightTasks >= maxConcurrentTasks) {
            res.setHeader('retry-after', '5');
            throw new HttpError(503, 'gateway paid-task capacity is full; retry shortly');
          }
          const idempotencyHeader = req.headers['x-idempotency-key'];
          if (idempotencyHeader !== undefined && (Array.isArray(idempotencyHeader) || idempotencyHeader.length > 200)) {
            throw new HttpError(400, 'x-idempotency-key must be at most 200 characters');
          }
          const idempotencyKey = Array.isArray(idempotencyHeader) ? undefined : idempotencyHeader;
          inFlightTasks += 1;
          try {
            const client = await getClient();
            const result = await invokeAgent(
              client,
              agentName,
              request,
              taskTimeoutMs,
              maxProgressEvents,
              idempotencyKey,
            );
            sendJson(res, 200, result);
          } finally {
            inFlightTasks -= 1;
          }
          return;
        }

        await drainRequest(req, maxBodyBytes);
        throw new HttpError(404, `no route for ${req.method ?? ''} ${pathname}`);
      } catch (err) {
        if (err instanceof HttpError) {
          sendJson(res, err.status, { error: err.message });
        } else {
          console.error('[gateway] dispatch failed:', err);
          sendJson(res, 500, { error: 'gateway dispatch failed' });
        }
      }
    })();
  });

  return { server, destroy };
}
