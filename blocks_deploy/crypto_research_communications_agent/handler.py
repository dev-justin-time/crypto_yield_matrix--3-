"""Native Blocks adapter for crypto_research_communications_agent."""

from __future__ import annotations

from typing import Optional
from blocks_network import StartTaskMessage, TaskContext
from blocks_agents.handlers.crypto_research_communications_agent import handler as local_handler


def handler(task: StartTaskMessage, ctx: Optional[TaskContext] = None) -> dict:
    return local_handler(task, ctx)
