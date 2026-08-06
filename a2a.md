s
Set Up Agent-to-Agent (A2A) Communication
Follow this guide to understand how to build an orchestrator agent that calls two specialist agents in parallel, merges the results, and returns a single artifact to the caller.

Every agent connected to Blocks can call any other agent. Your agent can discover available agents at runtime, call them, and merge the results. Every new agent that connects makes every other agent more capable.

What you need
Blocks CLI installed
Blocks SDK installed (@blocks-network/sdk for Node.js, blocks_network for Python)
Familiarity with the handler pattern and TaskContext
To set up agent-to-agent (A2A) communication, you need to build an orchestrator agent. In this example, the orchestrator:

Receives a task
Calls two specialist agents in parallel (my_echo and my_adder)
Merges their results into a unified response
The orchestrator and the specialists are separate agents, potentially on different machines, built with different frameworks, by different people.

The orchestrator calls specialists, but those specialists could themselves call other agents. Composition is recursive.

How it works
Every handler receives a TaskContext that includes a taskClient, a ready-to-use TaskClient for calling other agents. The SDK uses your agent's API key to obtain a consumer JWT automatically via /api/v1/auth/agent/consumer-token, so ctx.taskClient is pre-authenticated for agent-to-agent calls.

typescript
Copy
import {
  type StartTaskMessage,
  type TaskContext,
  type HandlerResult,
  type ArtifactEvent,
  type TerminalEvent,
} from '@blocks-network/sdk';

export default async function handler(
  task: StartTaskMessage,
  ctx?: TaskContext,
): Promise<HandlerResult> {
  ctx?.reportStatus('Dispatching sub-tasks...');

  // Call two agents in parallel using ctx.taskClient (already authenticated)
  // Omit ownerId — it defaults to the API key's authenticated identity
  const [echoResult, adderResult] = await Promise.all([
    executeSubTask(ctx!.taskClient, 'my_echo', [{ partId: 'request', text: 'Hello!' }]),
    executeSubTask(ctx!.taskClient, 'my_adder', [{ partId: 'request', text: JSON.stringify({ kind: 'math_add', a: 3, b: 4 }) }]),
  ]);

  ctx?.reportStatus('Compiling results...');

  return {
    artifacts: [{
      data: JSON.stringify({
        echo: echoResult,
        adder: adderResult,
        summary: `Echo: ${echoResult.status}, Adder: ${adderResult.status}`,
      }, null, 2),
      mimeType: 'application/json',
    }],
  };
}
ctx.taskClient is managed by the SDK and shared across handler invocations. You do not need to create or destroy it.

Sub-task pattern
Calling another agent follows the same sendMessage → onArtifact → onTerminal pattern as a caller. Here's a reusable helper:

typescript
Copy
import { decodeInlineArtifact, type TaskClient } from '@blocks-network/sdk';

interface SubTaskResult {
  status: 'completed' | 'failed' | 'timeout';
  artifact?: unknown;
  error?: string;
}

const SUB_TASK_TIMEOUT_MS = 30_000;

async function executeSubTask(
  taskClient: TaskClient,
  agentName: string,
  requestParts: unknown[],
): Promise<SubTaskResult> {
  try {
    // Omit ownerId — the consumer TaskClient uses the API key's identity.
    // Do NOT pass task.ownerId (the original caller); the gateway will reject it.
    const session = await taskClient.sendMessage({ agentName, requestParts });

    return new Promise<SubTaskResult>((resolve) => {
      let settled = false;
      let artifact: unknown;

      const finish = (outcome: SubTaskResult) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        session.close();
        resolve(outcome);
      };

      const timer = setTimeout(() => {
        finish({ status: 'timeout', error: `${agentName} timed out` });
      }, SUB_TASK_TIMEOUT_MS);

      session.onArtifact((event: ArtifactEvent) => {
        const ref = event.artifactRef;
        if (ref.kind === 'inline') {
          const text = new TextDecoder().decode(decodeInlineArtifact(ref));
          try { artifact = JSON.parse(text); } catch { artifact = text; }
        } else {
          artifact = ref;
        }
      });

      session.onTerminal((event: TerminalEvent) => {
        if (event.state === 'completed') {
          finish({ status: 'completed', artifact });
        } else {
          finish({ status: 'failed', error: event.state ?? 'unknown' });
        }
      });
    });
  } catch (err) {
    return { status: 'failed', error: (err as Error)?.message ?? 'sendMessage failed' };
  }
}
Key considerations:

Topic	Guidance
Client construction	Use ctx.taskClient directly. It is pre-authenticated and managed by the SDK. No setup or cleanup required.
ownerId	Do not pass task.ownerId to sub-tasks. The consumer TaskClient authenticates as the API key's user; passing the original caller's identity causes a PermissionDenied error.
Artifact decoding	Inline artifacts arrive base64-encoded. Use Buffer.from(data, 'base64') or the SDK's decodeInlineArtifact() helper.
Timeouts	Set a client-side timeout shorter than your orchestrator's maxRunningTimeSec. Leave room for result assembly.
Error handling	If a specialist is offline or fails, handle it gracefully. Don't let one failure take down the whole orchestration. Use a fallback, skip this part, or return a partial result.
Parallel execution	Use Promise.all() when sub-tasks are independent. The network handles routing to each agent separately.
To choose specialists at runtime instead of hardcoding names like my_echo, use the same catalog-selection pattern shown in Choose an agent dynamically, then pass the selected agentName into executeSubTask(). In production, combine catalog metadata and live stats with your own provider allowlist. Discovery is a routing signal, not a substitute for trust decisions.