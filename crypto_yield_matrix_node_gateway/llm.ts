import { lookup } from 'node:dns/promises';

/**
 * LLM transport for the gateway.
 *
 * Ollama is the default local backend. Hosted inference is opt-in through a
 * server-configured HTTPS base URL and a per-request X-LLM-API-Key header.
 * Provider URLs are configuration-only; callers cannot select arbitrary URLs.
 */

export type LlmProvider = 'ollama' | 'hosted';

export interface LlmMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LlmChatRequest {
  provider?: LlmProvider;
  model?: string;
  messages: LlmMessage[];
  temperature?: number;
  maxTokens?: number;
}

export interface LlmChatResult {
  provider: LlmProvider;
  model: string;
  content: string;
  usage?: Record<string, number>;
}

export class LlmError extends Error {
  constructor(readonly status: 400 | 502 | 503 | 504, message: string) {
    super(message);
  }
}

export interface LlmService {
  chat(request: LlmChatRequest, userApiKey?: string): Promise<LlmChatResult>;
}

export interface LlmServiceOptions {
  defaultProvider?: LlmProvider;
  ollamaBaseUrl?: string;
  ollamaModel?: string;
  hostedBaseUrl?: string;
  hostedAllowedHosts?: ReadonlySet<string>;
  timeoutMs?: number;
  maxResponseBytes?: number;
  maxMessageChars?: number;
  maxTotalMessageChars?: number;
}

const DEFAULT_OLLAMA_URL = 'http://127.0.0.1:11434';
const DEFAULT_OLLAMA_MODEL = 'llama3.2:3b';
const DEFAULT_TIMEOUT_MS = 120_000;
const DEFAULT_MAX_MESSAGE_CHARS = 16_000;
const DEFAULT_MAX_TOTAL_MESSAGE_CHARS = 50_000;

function localHost(hostname: string): boolean {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, '');
  return host === 'localhost' || host === '127.0.0.1' || host === '::1';
}

function disallowedHostedHost(hostname: string): boolean {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, '');
  if (localHost(host) || host === 'metadata.google.internal' || host.endsWith('.internal') || host.endsWith('.local')) return true;
  const octets = host.split('.').map(Number);
  if (octets.length !== 4 || octets.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return false;
  const [a, b] = octets;
  return a === 10 || a === 127 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 169 && b === 254);
}

function configuredUrl(raw: string, name: string, localOnly: boolean, allowedHosts?: ReadonlySet<string>): string {
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(`${name} must be an absolute URL`);
  }
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error(`${name} must use http/https without credentials, query, or fragment`);
  }
  if (localOnly && (!localHost(parsed.hostname) || parsed.protocol !== 'http:')) {
    throw new Error(`${name} must point to local Ollama over http://localhost or loopback`);
  }
  if (!localOnly && parsed.protocol !== 'https:') {
    throw new Error(`${name} must use HTTPS for hosted inference`);
  }
  if (!localOnly && disallowedHostedHost(parsed.hostname)) {
    throw new Error(`${name} must not target loopback, private, link-local, metadata, or internal hosts`);
  }
  if (!localOnly && (!allowedHosts || !allowedHosts.has(parsed.hostname.toLowerCase()))) {
    throw new Error(`${name} hostname is not in the configured LLM_HOSTED_ALLOWED_HOSTS allowlist`);
  }
  return raw.replace(/\/$/, '');
}

function modelName(raw: string, name: string): string {
  if (!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(raw)) {
    throw new LlmError(400, `${name} contains unsupported characters`);
  }
  return raw;
}

function validateRequest(request: LlmChatRequest, maxMessageChars: number, maxTotalMessageChars: number): LlmChatRequest {
  if (!request || !Array.isArray(request.messages) || request.messages.length === 0 || request.messages.length > 100) {
    throw new LlmError(400, 'messages must be a non-empty array of at most 100 items');
  }
  let total = 0;
  const messages = request.messages.map((message) => {
    if (!message || !['system', 'user', 'assistant'].includes(message.role) || typeof message.content !== 'string' || message.content.length > maxMessageChars) {
      throw new LlmError(400, `each message requires a valid role and content of at most ${maxMessageChars} characters`);
    }
    total += message.content.length;
    return { role: message.role, content: message.content };
  });
  if (total > maxTotalMessageChars) {
    throw new LlmError(400, `combined message content exceeds ${maxTotalMessageChars} characters`);
  }
  if (request.provider !== undefined && !['ollama', 'hosted'].includes(request.provider)) {
    throw new LlmError(400, 'provider must be ollama or hosted');
  }
  if (request.model !== undefined) modelName(request.model, 'model');
  if (request.temperature !== undefined && (!Number.isFinite(request.temperature) || request.temperature < 0 || request.temperature > 2)) {
    throw new LlmError(400, 'temperature must be between 0 and 2');
  }
  if (request.maxTokens !== undefined && (!Number.isInteger(request.maxTokens) || request.maxTokens < 1 || request.maxTokens > 32_768)) {
    throw new LlmError(400, 'maxTokens must be an integer between 1 and 32768');
  }
  return { ...request, messages };
}

async function assertPublicHostedDestination(baseUrl: string): Promise<void> {
  const hostname = new URL(baseUrl).hostname;
  const addresses = await lookup(hostname, { all: true, verbatim: true });
  if (addresses.length === 0 || addresses.some((entry) => disallowedHostedHost(entry.address))) {
    throw new LlmError(503, 'hosted LLM endpoint resolved to a private or otherwise disallowed address');
  }
}

async function readBoundedText(response: Response, maxBytes: number): Promise<string> {
  const declared = response.headers.get('content-length');
  if (declared && Number(declared) > maxBytes) {
    throw new LlmError(502, 'LLM response exceeds the configured size limit');
  }
  if (!response.body) {
    const text = await response.text();
    if (Buffer.byteLength(text, 'utf8') > maxBytes) throw new LlmError(502, 'LLM response exceeds the configured size limit');
    return text;
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      total += part.value.byteLength;
      if (total > maxBytes) {
        await reader.cancel();
        throw new LlmError(502, 'LLM response exceeds the configured size limit');
      }
      chunks.push(part.value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return new TextDecoder().decode(bytes);
}

function abortableFetch(input: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(input, { ...init, redirect: 'error', signal: controller.signal }).finally(() => clearTimeout(timer));
}

async function parseResponse(response: Response, provider: LlmProvider, model: string, maxResponseBytes: number): Promise<LlmChatResult> {
  const raw = await readBoundedText(response, maxResponseBytes);
  if (!response.ok) {
    throw new LlmError(502, `LLM ${provider} upstream returned HTTP ${response.status}`);
  }
  let body: any;
  try {
    body = JSON.parse(raw);
  } catch {
    throw new LlmError(502, `LLM ${provider} upstream returned invalid JSON`);
  }
  const content = provider === 'ollama' ? body?.message?.content : body?.choices?.[0]?.message?.content;
  if (typeof content !== 'string') {
    throw new LlmError(502, `LLM ${provider} upstream response did not contain assistant content`);
  }
  const usage = provider === 'hosted' && body?.usage && typeof body.usage === 'object'
    ? Object.fromEntries(Object.entries(body.usage).filter((entry): entry is [string, number] => typeof entry[1] === 'number'))
    : undefined;
  return { provider, model, content, ...(usage && Object.keys(usage).length > 0 ? { usage } : {}) };
}

export function createLlmService(options: LlmServiceOptions = {}): LlmService {
  const defaultProvider = options.defaultProvider ?? 'ollama';
  const ollamaBaseUrl = configuredUrl(options.ollamaBaseUrl ?? DEFAULT_OLLAMA_URL, 'OLLAMA_BASE_URL', true);
  const ollamaModel = modelName(options.ollamaModel ?? DEFAULT_OLLAMA_MODEL, 'OLLAMA_MODEL');
  const hostedBaseUrl = options.hostedBaseUrl ? configuredUrl(options.hostedBaseUrl, 'LLM_HOSTED_BASE_URL', false, options.hostedAllowedHosts) : undefined;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const maxResponseBytes = options.maxResponseBytes ?? 1_000_000;
  const maxMessageChars = options.maxMessageChars ?? DEFAULT_MAX_MESSAGE_CHARS;
  const maxTotalMessageChars = options.maxTotalMessageChars ?? DEFAULT_MAX_TOTAL_MESSAGE_CHARS;
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1) throw new Error('LLM timeout must be a positive integer');
  if (!Number.isInteger(maxResponseBytes) || maxResponseBytes < 1) throw new Error('LLM response size must be a positive integer');
  if (defaultProvider === 'hosted' && !hostedBaseUrl) throw new Error('hosted default requires LLM_HOSTED_BASE_URL');

  return {
    async chat(input: LlmChatRequest, userApiKey?: string): Promise<LlmChatResult> {
      const request = validateRequest(input, maxMessageChars, maxTotalMessageChars);
      const provider = request.provider ?? defaultProvider;
      const model = modelName(request.model ?? (provider === 'ollama' ? ollamaModel : 'hosted-default'), 'model');
      if (provider === 'hosted' && !hostedBaseUrl) {
        throw new LlmError(503, 'hosted inference is not configured by the gateway operator');
      }
      if (provider === 'hosted' && (!userApiKey || userApiKey.length < 16 || userApiKey.length > 512 || /[\r\n\t\s]/.test(userApiKey))) {
        throw new LlmError(400, 'hosted inference requires a valid single-value X-LLM-API-Key');
      }
      const url = provider === 'ollama'
        ? `${ollamaBaseUrl}/api/chat`
        : `${hostedBaseUrl}/v1/chat/completions`;
      const headers: Record<string, string> = { 'content-type': 'application/json' };
      if (provider === 'hosted') headers.authorization = `Bearer ${userApiKey}`;
      const body = {
        model,
        messages: request.messages,
        stream: false,
        ...(request.temperature !== undefined ? { temperature: request.temperature } : {}),
        ...(request.maxTokens !== undefined ? provider === 'ollama' ? { options: { num_predict: request.maxTokens } } : { max_tokens: request.maxTokens } : {}),
      };
      try {
        if (provider === 'hosted') await assertPublicHostedDestination(url);
        const response = await abortableFetch(url, {
          method: 'POST',
          headers,
          body: JSON.stringify(body),
        }, timeoutMs);
        return await parseResponse(response, provider, model, maxResponseBytes);
      } catch (error) {
        if (error instanceof LlmError) throw error;
        if (error instanceof DOMException && error.name === 'AbortError') throw new LlmError(504, 'LLM upstream request timed out');
        throw new LlmError(502, 'LLM upstream request failed');
      }
    },
  };
}

export function createLlmServiceFromEnv(env: NodeJS.ProcessEnv = process.env): LlmService {
  const defaultProvider = env.LLM_DEFAULT_PROVIDER === 'hosted' ? 'hosted' : 'ollama';
  return createLlmService({
    defaultProvider,
    ollamaBaseUrl: env.OLLAMA_BASE_URL,
    ollamaModel: env.OLLAMA_MODEL,
    hostedBaseUrl: env.LLM_HOSTED_BASE_URL,
    hostedAllowedHosts: new Set((env.LLM_HOSTED_ALLOWED_HOSTS ?? '').split(',').map((host) => host.trim().toLowerCase()).filter(Boolean)),
    timeoutMs: env.LLM_TIMEOUT_MS ? Number(env.LLM_TIMEOUT_MS) : undefined,
    maxResponseBytes: env.LLM_MAX_RESPONSE_BYTES ? Number(env.LLM_MAX_RESPONSE_BYTES) : undefined,
  });
}
