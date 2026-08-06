"""Native Blocks adapter for portfolio_scenario_expert."""

from __future__ import annotations

from typing import Optional
from blocks_network import StartTaskMessage, TaskContext
from blocks_agents.handlers.portfolio_scenario_expert import handler as local_handler


def handler(task: StartTaskMessage, ctx: Optional[TaskContext] = None) -> dict:
    return local_handler(task, ctx)
