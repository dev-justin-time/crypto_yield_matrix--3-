/**
 * Single-instance gateway for all 12 published Blocks agents.
 *
 * One Node.js process owns a single shared `TaskClient` and exposes a small
 * authenticated HTTP API. The Blocks API key remains server-side; callers
 * authenticate with a separate gateway client key.
 *
 *   GET  /health                  -> public liveness + fleet summary
 *   GET  /ready                   -> public configuration/readiness summary
 *   GET  /agents                  -> public served-agent catalog
 *   POST /agents/:name/invoke     -> authenticated paid task dispatch
 *
 * The request body is forwarded verbatim to the agent's `request` part, so
 * handler-specific fields (question, symbol, category, source_file, ...)
 * pass through unchanged.
 */
import { randomUUID, timingSafeEqual } from 'node:crypto';
import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
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
const DEFAULT_TASK_COST_USD = 0.10;
const DEFAULT_DAILY_TASKS = 100;
const DEFAULT_DAILY_SPEND_USD = 10;
const DEFAULT_REQUESTS_PER_MINUTE = 30;
const DEFAULT_MAX_QUESTION_CHARS = 4_000;

export interface GatewayOptions {
  apiKey: string;
  /** Gateway client id -> bearer secret. Never use the Blocks API key here. */
  clientKeys: Readonly<Record<string, string>>;
  /** Optional client id -> allowed agent names. Missing ids may use '*'. */
  clientAgents?: Readonly<Record<string, ReadonlySet<string>>>;
  taskTimeoutMs?: number;
  maxBodyBytes?: number;
  maxProgressEvents?: number;
  maxQuestionChars?: number;
  /** Maximum number of paid tasks this gateway will have in flight. */
  maxConcurrentTasks?: number;
  /** Per-client rolling-window request limit. */
  maxRequestsPerMinute?: number;
  /** Conservative accepted-task budget for this gateway process per UTC day. */
  maxDailyTasks?: number;
  /** Conservative accepted-task spend budget for this gateway process per UTC day. */
  maxDailySpendUsd?: number;
  /** Estimated Blocks charge reserved for each accepted task. */
  taskCostUsd?: number;
  /** Optional no-spend factory used by tests; production uses TaskClient.create. */
  taskClientFactory?: () => Promise<TaskClient>;
  /** Optional durable JSON ledger path for a single gateway instance. */
  budgetStateFile?: string;
}

export interface Gateway {
  server: ReturnType<typeof createServer>;
  /** Destroy the shared SDK client. Safe to call once (e.g. on shutdown). */
  destroy(): Promise<void>;
}

interface ClientWindow {
  startedAt: number;
  requests: number;
}

interface BudgetState {
  day: string;
  tasks: number;
  spendUsd: number;
}

interface AuthenticatedClient {
  id: string;
}

class HttpError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly retryAfterSeconds?: number,
  ) {
    super(message);
  }
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(payload),
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
  });
  res.end(payload);
}

function logEvent(event: Record<string, unknown>): void {
  // Never include request payloads, bearer secrets, or the Blocks API key.
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    service: 'crypto_yield_matrix_node_gateway',
    ...event,
  }));
}

function requestId(req: IncomingMessage): string {
  const supplied = req.headers['x-request-id'];
  if (typeof supplied === 'string' && /^[A-Za-z0-9._:-]{1,128}$/.test(supplied)) {
    return supplied;
  }
  return randomUUID();
}

function equalSecret(left: string, right: string): boolean {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

function authenticate(req: IncomingMessage, clientKeys: Readonly<Record<string, string>>): AuthenticatedClient {
  const header = req.headers.authorization;
  if (typeof header !== 'string' || !header.startsWith('Bearer ')) {
    throw new HttpError(401, 'authentication required');
  }
  const token = header.slice('Bearer '.length).trim();
  if (token.length < 16 || token.length > 512) {
    throw new HttpError(401, 'invalid gateway credentials');
  }
  for (const [id, secret] of Object.entries(clientKeys)) {
    if (equalSecret(token, secret)) {
      return { id };
    }
  }
  throw new HttpError(401, 'invalid gateway credentials');
}

function positiveInteger(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 1) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

function nonnegativeNumber(value: number, name: string): number {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error(`${name} must be a non-negative finite number`);
  }
  return value;
}

function utcDay(): string {
  return new Date().toISOString().slice(0, 10);
}

function secondsUntilNextUtcDay(): number {
  const now = new Date();
  const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
  return Math.max(1, Math.ceil((next.getTime() - now.getTime()) / 1_000));
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
  requestId: string;
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
  idempotencyKey: string | undefined,
  correlationId: string,
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
    requestId: correlationId,
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

export function parseClientKeys(raw: string): Record<string, string> {
  const keys: Record<string, string> = {};
  for (const entry of raw.split(',')) {
    const trimmed = entry.trim();
    if (!trimmed) continue;
    const separator = trimmed.indexOf('=');
    if (separator <= 0) {
      throw new Error('GATEWAY_CLIENT_KEYS entries must use clientId=secret format');
    }
    const id = trimmed.slice(0, separator).trim();
    const secret = trimmed.slice(separator + 1).trim();
    if (!/^[A-Za-z0-9_.-]{1,64}$/.test(id) || secret.length < 16) {
      throw new Error('gateway client ids must be safe names and secrets must be at least 16 characters');
    }
    if (keys[id]) {
      throw new Error(`duplicate gateway client id '${id}'`);
    }
    keys[id] = secret;
  }
  if (Object.keys(keys).length === 0) {
    throw new Error('GATEWAY_CLIENT_KEYS must configure at least one client');
  }
  return keys;
}

export function parseClientAgents(raw: string | undefined): Record<string, ReadonlySet<string>> {
  if (!raw || !raw.trim()) return {};
  const result: Record<string, ReadonlySet<string>> = {};
  for (const entry of raw.split(',')) {
    const separator = entry.indexOf('=');
    if (separator <= 0) throw new Error('GATEWAY_CLIENT_AGENTS entries must use clientId=agent|agent format');
    const id = entry.slice(0, separator).trim();
    const agents = entry.slice(separator + 1).split('|').map((name) => name.trim()).filter(Boolean);
    if (!/^[A-Za-z0-9_.-]{1,64}$/.test(id) || agents.length === 0 || agents.some((name) => !getAgent(name))) {
      throw new Error(`invalid gateway agent allowlist for client '${id}'`);
    }
    result[id] = new Set(agents);
  }
  return result;
}

export function createGateway(options: GatewayOptions): Gateway {
  const taskTimeoutMs = options.taskTimeoutMs ?? 120_000;
  const maxBodyBytes = options.maxBodyBytes ?? 1_000_000;
  const maxProgressEvents = options.maxProgressEvents ?? 50;
  const maxQuestionChars = options.maxQuestionChars ?? DEFAULT_MAX_QUESTION_CHARS;
  const maxConcurrentTasks = options.maxConcurrentTasks ?? 8;
  const maxRequestsPerMinute = options.maxRequestsPerMinute ?? DEFAULT_REQUESTS_PER_MINUTE;
  const maxDailyTasks = options.maxDailyTasks ?? DEFAULT_DAILY_TASKS;
  const maxDailySpendUsd = options.maxDailySpendUsd ?? DEFAULT_DAILY_SPEND_USD;
  const taskCostUsd = options.taskCostUsd ?? DEFAULT_TASK_COST_USD;
  positiveInteger(taskTimeoutMs, 'taskTimeoutMs');
  positiveInteger(maxBodyBytes, 'maxBodyBytes');
  positiveInteger(maxProgressEvents, 'maxProgressEvents');
  positiveInteger(maxQuestionChars, 'maxQuestionChars');
  positiveInteger(maxConcurrentTasks, 'maxConcurrentTasks');
  positiveInteger(maxRequestsPerMinute, 'maxRequestsPerMinute');
  positiveInteger(maxDailyTasks, 'maxDailyTasks');
  positiveInteger(Object.keys(options.clientKeys).length, 'clientKeys');
  if (Object.values(options.clientKeys).some((secret) => equalSecret(secret, options.apiKey))) {
    throw new Error('gateway client secrets must not equal the Blocks API key');
  }
  nonnegativeNumber(maxDailySpendUsd, 'maxDailySpendUsd');
  nonnegativeNumber(taskCostUsd, 'taskCostUsd');
  if (taskCostUsd <= 0) throw new Error('taskCostUsd must be greater than zero');

  let inFlightTasks = 0;
  let clientPromise: Promise<TaskClient> | null = null;
  let clientReady = false;
  const clientWindows = new Map<string, ClientWindow>();
  let budget: BudgetState = { day: utcDay(), tasks: 0, spendUsd: 0 };
  if (options.budgetStateFile && existsSync(options.budgetStateFile)) {
    try {
      const parsed = JSON.parse(readFileSync(options.budgetStateFile, 'utf8')) as Partial<BudgetState>;
      const tasks = parsed.tasks;
      const spendUsd = parsed.spendUsd;
      if (typeof parsed.day === 'string' && Number.isInteger(tasks) && tasks >= 0 && typeof spendUsd === 'number' && Number.isFinite(spendUsd) && spendUsd >= 0) {
        budget = { day: parsed.day, tasks, spendUsd };
      }
    } catch {
      throw new Error(`unable to read gateway budget state '${options.budgetStateFile}'`);
    }
  }

  const persistBudget = (): void => {
    if (!options.budgetStateFile) return;
    const temporary = `${options.budgetStateFile}.${process.pid}.tmp`;
    writeFileSync(temporary, JSON.stringify(budget), { encoding: 'utf8', mode: 0o600 });
    renameSync(temporary, options.budgetStateFile);
  };

  const resetBudgetIfNeeded = (): void => {
    const day = utcDay();
    if (budget.day !== day) {
      budget = { day, tasks: 0, spendUsd: 0 };
      persistBudget();
    }
  };

  const reserveBudget = (clientId: string): void => {
    resetBudgetIfNeeded();
    const now = Date.now();
    const window = clientWindows.get(clientId);
    if (!window || now - window.startedAt >= 60_000) {
      clientWindows.set(clientId, { startedAt: now, requests: 1 });
    } else {
      if (window.requests >= maxRequestsPerMinute) {
        const retryAfter = Math.max(1, Math.ceil((60_000 - (now - window.startedAt)) / 1_000));
        throw new HttpError(429, 'client request rate limit exceeded', retryAfter);
      }
      window.requests += 1;
    }
    if (budget.tasks >= maxDailyTasks || budget.spendUsd + taskCostUsd > maxDailySpendUsd) {
      throw new HttpError(429, 'gateway daily paid-task budget exhausted', secondsUntilNextUtcDay());
    }
    // Reserve before yielding to the SDK. Failed or canceled attempts remain
    // counted conservatively because the remote billing outcome is uncertain.
    budget.tasks += 1;
    budget.spendUsd = Number((budget.spendUsd + taskCostUsd).toFixed(2));
    persistBudget();
  };

  const getClient = async (): Promise<TaskClient> => {
    if (!clientPromise) {
      clientPromise = options.taskClientFactory
        ? options.taskClientFactory()
        : TaskClient.create({
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
    const correlationId = requestId(req);
    res.setHeader('x-request-id', correlationId);
    const startedAt = Date.now();
    void (async () => {
      let clientId: string | undefined;
      let agentName: string | undefined;
      try {
        const url = new URL(req.url ?? '/', 'http://localhost');
        const { pathname } = url;

        if (req.method === 'GET' && pathname === '/health') {
          sendJson(res, 200, {
            status: 'ok',
            uptimeSeconds: Math.round(process.uptime()),
            agents: AGENTS.length,
            billingMode: BILLING_MODE,
            authRequired: true,
            inFlightTasks,
            maxConcurrentTasks,
          });
          return;
        }

        if (req.method === 'GET' && pathname === '/ready') {
          try {
            await getClient();
          } catch {
            throw new HttpError(503, 'Blocks client is not ready; no task was dispatched');
          }
          resetBudgetIfNeeded();
          const budgetAvailable = budget.tasks < maxDailyTasks && budget.spendUsd + taskCostUsd <= maxDailySpendUsd;
          sendJson(res, budgetAvailable ? 200 : 503, {
            status: budgetAvailable ? 'ready' : 'budget_exhausted',
            configurationReady: true,
            // Readiness initializes the SDK client but never sends a task;
            // a successful paid canary is still required before promotion.
            clientReady,
            agents: AGENTS.length,
            billingMode: BILLING_MODE,
            budget: {
              day: budget.day,
              reservedTasks: budget.tasks,
              maxDailyTasks,
              reservedSpendUsd: budget.spendUsd,
              maxDailySpendUsd,
              taskCostUsd,
            },
          });
          return;
        }

        if (req.method === 'GET' && pathname === '/agents') {
          sendJson(res, 200, { agents: AGENTS });
          return;
        }

        const invokeMatch = pathname.match(/^\/agents\/([A-Za-z0-9_]+)\/invoke$/);
        if (req.method === 'POST' && invokeMatch) {
          agentName = invokeMatch[1];
          // Always consume the request body before any early exit so the
          // keep-alive connection stays in sync for the next request.
          const payload = await readJsonBody(req, maxBodyBytes);
          const client = authenticate(req, options.clientKeys);
          clientId = client.id;
          if (!getAgent(agentName)) {
            throw new HttpError(404, `unknown agent '${agentName}'`);
          }
          const allowedAgents = options.clientAgents?.[clientId];
          if (allowedAgents && !allowedAgents.has(agentName)) {
            throw new HttpError(403, 'gateway client is not authorized for this agent');
          }
          if (req.headers['content-type'] && !req.headers['content-type'].toLowerCase().includes('application/json')) {
            throw new HttpError(415, 'content-type must be application/json');
          }
          if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
            throw new HttpError(400, 'request body must be a JSON object');
          }
          const request = payload as Record<string, unknown>;
          if (request.source_file !== undefined && request.source_file !== 'yield_data.csv') {
            throw new HttpError(400, 'source_file must be the canonical yield_data.csv');
          }
          if (typeof request.question !== 'string' || request.question.trim() === '') {
            throw new HttpError(400, 'request body requires a non-empty string question');
          }
          if (request.question.length > maxQuestionChars) {
            throw new HttpError(413, `question exceeds ${maxQuestionChars} characters`);
          }
          if (inFlightTasks >= maxConcurrentTasks) {
            res.setHeader('retry-after', '5');
            throw new HttpError(503, 'gateway paid-task capacity is full; retry shortly', 5);
          }
          const idempotencyHeader = req.headers['x-idempotency-key'];
          if (idempotencyHeader !== undefined && (Array.isArray(idempotencyHeader) || idempotencyHeader.length > 200)) {
            throw new HttpError(400, 'x-idempotency-key must be at most 200 characters');
          }
          const idempotencyKey = Array.isArray(idempotencyHeader) ? undefined : idempotencyHeader;
          reserveBudget(clientId);
          inFlightTasks += 1;
          try {
            const blocksClient = await getClient();
            const result = await invokeAgent(
              blocksClient,
              agentName,
              request,
              taskTimeoutMs,
              maxProgressEvents,
              idempotencyKey,
              correlationId,
            );
            sendJson(res, 200, result);
          } finally {
            inFlightTasks -= 1;
          }
          logEvent({ event: 'invoke_complete', requestId: correlationId, clientId, agent: agentName, durationMs: Date.now() - startedAt });
          return;
        }

        await drainRequest(req, maxBodyBytes);
        throw new HttpError(404, `no route for ${req.method ?? ''} ${pathname}`);
      } catch (err) {
        const status = err instanceof HttpError ? err.status : 500;
        const message = err instanceof HttpError ? err.message : 'gateway dispatch failed';
        if (err instanceof HttpError && err.retryAfterSeconds !== undefined) {
          res.setHeader('retry-after', String(err.retryAfterSeconds));
        }
        logEvent({
          event: 'request_rejected',
          requestId: correlationId,
          clientId,
          agent: agentName,
          status,
          durationMs: Date.now() - startedAt,
          error: message,
        });
        sendJson(res, status, { error: message, requestId: correlationId });
      }
    })();
  });

  return { server, destroy };
}
