import json
from threading import Thread

from handler import merge_results, request_payload


class Part:
    def __init__(self, text):
        self.text = text


class Task:
    def __init__(self, payload):
        self.request_parts = [Part(json.dumps(payload))]


def test_request_payload():
    assert request_payload(Task({"question": "test", "symbol": "BTC"})) == {"question": "test", "symbol": "BTC"}


def test_merge_partial_results():
    results = [
        {"agent": "crypto_risk_analyst", "status": "completed", "artifact": {"status": "PASS", "findings": [{"risk": 1}], "assumptions": [], "limitations": [], "provenance": {"source_file": "yield_data.csv", "context_files": ["DATA_DICTIONARY.md"]}}},
        {"agent": "defi_liquidity_analyst", "status": "timeout", "error": "specialist timed out"},
    ]
    output = merge_results(results, {"question": "test", "symbol": "BTC", "source_file": "yield_data.csv"})
    assert output["status"] == "WARNING"
    assert output["findings"][0] == {"risk": 1}
    assert output["provenance"]["source_file"] == "yield_data.csv"
    assert output["provenance"]["context_files"] == ["DATA_DICTIONARY.md"]
    assert {"decision_use", "review_next", "do_not_infer"} <= set(output["user_value"])


def test_non_object_artifact_warns():
    output = merge_results([{"agent": "specialist", "status": "completed", "artifact": "not-json"}], {"question": "test"})
    assert output["status"] == "WARNING"


if __name__ == "__main__":
    test_request_payload()
    test_merge_partial_results()
    test_non_object_artifact_warns()
    print("A2A mocked tests pass")
