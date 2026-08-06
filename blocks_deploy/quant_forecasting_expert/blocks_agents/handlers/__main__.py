"""Run a minimal smoke test for every indexed local agent card."""

import json
from dataclasses import dataclass

from ..loader import run_card


@dataclass
class Part:
    text: str


@dataclass
class Task:
    request_parts: list[Part]


if __name__ == "__main__":
    index = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "agent_cards.json").read_text())
    task = Task([Part('{"question":"smoke test", "symbol":"BTC"}')])
    for card in index["agents"]:
        result = run_card(card, task)
        assert result["artifacts"][0]["mimeType"] == "application/json"
        print(f"{card}: ok")
