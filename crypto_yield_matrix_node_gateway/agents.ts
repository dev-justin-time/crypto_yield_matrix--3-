/**
 * Registry of the Blocks agents served by this gateway.
 *
 * Names must match the agents published on the Blocks Network exactly; they
 * are used as the task's `agentName`. All agents in this fleet are published
 * with paid billing at $0.10/task.
 */
export interface AgentInfo {
  /** Published Blocks agent name (used as the task's `agentName`). */
  name: string;
  /** Short description of what the agent does. */
  description: string;
  /** Typical request fields the agent understands (passed through verbatim). */
  requestFields: string[];
}

export const AGENTS: readonly AgentInfo[] = [
  {
    name: 'crypto_research_communications_agent',
    description: 'Produces cautious, evidence-linked research notes.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
  {
    name: 'crypto_risk_analyst',
    description: 'Places yield beside volatility, drawdown, beta, and Sharpe-like metrics.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
  {
    name: 'crypto_yield_a2a_orchestrator',
    description: 'Calls the private specialist agents in parallel and merges partial failures into one JSON artifact.',
    requestFields: ['question', 'symbol', 'category', 'source_file', 'agents'],
  },
  {
    name: 'data_provenance_auditor',
    description: 'Audits schemas, source conflicts, hashes, and lineage.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
  {
    name: 'defi_liquidity_analyst',
    description: 'Reviews volume, TVL, addresses, transactions, and liquidity proxies.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
  {
    name: 'feature_engineering_expert',
    description: 'Recomputes four transparent derived yield, liquidity, risk, and peer features.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
  {
    name: 'matrix_research_insights_agent',
    description: 'Converts the dashboard matrix into traceable research insights.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
  {
    name: 'model_validation_guardian',
    description: 'Checks source duplication, leakage, target circularity, and time splits.',
    requestFields: ['question', 'symbol', 'category', 'source_file', 'features', 'target', 'split'],
  },
  {
    name: 'portfolio_scenario_expert',
    description: 'Explains educational yield, risk, and liquidity scenarios.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
  {
    name: 'quant_forecasting_expert',
    description: 'Designs cautious forecasts and enforces readiness gates.',
    requestFields: ['question', 'symbol', 'category', 'source_file', 'features', 'target', 'split'],
  },
  {
    name: 'tokenomics_sustainability_expert',
    description: 'Compares nominal yield with inflation and dilution pressure.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
  {
    name: 'yield_methodology_expert',
    description: 'Compares yield mechanisms, annualization, and methodology notes.',
    requestFields: ['question', 'symbol', 'category', 'source_file'],
  },
];

export const AGENT_NAMES: ReadonlySet<string> = new Set(AGENTS.map((agent) => agent.name));

export function getAgent(name: string): AgentInfo | undefined {
  return AGENTS.find((agent) => agent.name === name);
}
