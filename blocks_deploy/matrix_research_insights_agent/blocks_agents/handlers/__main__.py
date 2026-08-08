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
        artifact = result["artifacts"][0]
        assert artifact["mimeType"] == "application/json"
        payload = json.loads(artifact["data"])
        assert {"decision_use", "review_next", "do_not_infer"} <= set(payload["user_value"])
        assert {"available", "rows", "source_snapshot_rows", "canonical_only_rows", "policy"} <= set(payload["asset_catalog"])
        assert payload["provenance"]["source_file"] in {None, "yield_data.csv"}
        print(f"{card}: ok")
