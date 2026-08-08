"""Generated native Blocks adapter for crypto_research_communications_agent.

Source card: blocks_agents/crypto_research_communications_agent.json
Do not add business logic here; edit the source handler instead.
"""

from __future__ import annotations

from typing import Optional

from blocks_network import StartTaskMessage, TaskContext
from blocks_agents.handlers.crypto_research_communications_agent import handler as local_handler


def handler(task: StartTaskMessage, ctx: Optional[TaskContext] = None) -> dict:
    return local_handler(task, ctx)
