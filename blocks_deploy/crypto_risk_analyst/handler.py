"""Generated native Blocks adapter for crypto_risk_analyst.

Source card: blocks_agents/crypto_risk_analyst.json
Do not add business logic here; edit the source handler instead.
"""

from __future__ import annotations

from typing import Optional

from blocks_network import StartTaskMessage, TaskContext
from blocks_agents.handlers.crypto_risk_analyst import handler as local_handler


def handler(task: StartTaskMessage, ctx: Optional[TaskContext] = None) -> dict:
    return local_handler(task, ctx)
