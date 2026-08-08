/** No-network tests for the Ollama-default LLM adapter. */
import { createServer } from 'node:http';
import { createLlmService, LlmError } from './llm.js';

async function main(): Promise<void> {
  let receivedAuthorization: string | undefined;
  const server = createServer(async (req, res) => {
    if (req.method !== 'POST' || req.url !== '/api/chat') {
      res.writeHead(404).end();
      return;
    }
    receivedAuthorization = req.headers.authorization;
    let body = '';
    for await (const chunk of req) body += String(chunk);
    const request = JSON.parse(body) as { model: string; stream: boolean };
    if (request.model !== 'smoke-model' || request.stream !== false) {
      res.writeHead(400).end(JSON.stringify({ error: 'unexpected request' }));
      return;
    }
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ model: request.model, message: { role: 'assistant', content: 'local ollama ok' } }));
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('LLM smoke server did not bind');

  const service = createLlmService({
    ollamaBaseUrl: `http://127.0.0.1:${address.port}`,
    ollamaModel: 'smoke-model',
    timeoutMs: 1_000,
  });
  const result = await service.chat({ messages: [{ role: 'user', content: 'hello' }] });
  if (result.provider !== 'ollama' || result.content !== 'local ollama ok' || receivedAuthorization !== undefined) {
    throw new Error('Ollama default adapter contract failed');
  }

  const hosted = createLlmService({ hostedBaseUrl: 'https://llm.example.test', hostedAllowedHosts: new Set(['llm.example.test']) });
  await hosted.chat({ provider: 'hosted', messages: [{ role: 'user', content: 'hello' }] }).then(
    () => { throw new Error('hosted adapter accepted a missing user API key'); },
    (error: unknown) => {
      if (!(error instanceof Error) || !error.message.includes('X-LLM-API-Key')) throw error;
    },
  );

  let privateRejected = false;
  try {
    createLlmService({ hostedBaseUrl: 'https://127.0.0.1:8443', hostedAllowedHosts: new Set(['127.0.0.1']) });
  } catch (error) {
    privateRejected = error instanceof Error && error.message.includes('private');
  }
  if (!privateRejected) throw new Error('private hosted URL was accepted');
  try { await hosted.chat({ provider: 'hosted', messages: [{ role: 'user', content: 'hello' }] }, 'bad key with spaces'); throw new Error('invalid key was accepted'); } catch (error) {
    if (!(error instanceof LlmError) || error.status !== 400) throw error;
  }
  await new Promise<void>((resolve) => server.close(() => resolve()));
  console.log('llm smoke: PASS (Ollama default, no auth forwarding, hosted key/host/validation gates)');
}

main().catch((error) => {
  console.error('llm smoke: FAIL', error);
  process.exit(1);
});
