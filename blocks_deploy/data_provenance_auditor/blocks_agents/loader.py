from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent


def load_card(filename: str) -> tuple[dict[str, Any], Callable[..., Any]]:
    card_path = ROOT / filename
    card = json.loads(card_path.read_text(encoding="utf-8"))
    handler = card["runtime"]["handler"]
    if handler.startswith("./"):
        handler_path = (card_path.parent / handler[2:]).resolve()
        if handler_path.parent != (ROOT / "handlers").resolve():
            raise ValueError(f"handler escapes the scaffold handler directory: {handler}")
        module_name = f"blocks_agents.handlers.{handler_path.stem}"
    else:
        module_name = handler.replace("/", ".").removesuffix(".py")
    module: ModuleType = importlib.import_module(module_name)
    callback = getattr(module, "handler", None)
    if not callable(callback):
        raise TypeError(f"handler callable missing from {module_name}")
    return card, callback


def run_card(filename: str, task: Any, ctx: Any = None) -> Any:
    _, callback = load_card(filename)
    return callback(task, ctx)
