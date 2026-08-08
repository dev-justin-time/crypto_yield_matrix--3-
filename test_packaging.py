"""No-spend packaging and behavioral smoke tests.

These tests never invoke the Blocks SDK or network. They exercise the local
source scaffold and the materialized crypto_risk_analyst deployment package.
Run with ``python test_packaging.py``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPLOYMENT = ROOT / "blocks_deploy" / "crypto_risk_analyst"


def run_python(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("BLOCKS_API_KEY", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, env=env, text=True,
        capture_output=True, check=False,
    )


class PackagingTests(unittest.TestCase):
    def test_source_scaffold_smoke(self) -> None:
        result = run_python("-m", "blocks_agents.handlers")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("crypto_risk_analyst.json: ok", result.stdout)

    def test_generated_contracts_are_current(self) -> None:
        for command in [("generate_deployments.py", "--check"), ("sync_deployments.py", "--check")]:
            with self.subTest(command=command):
                result = run_python(*command)
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_materialized_deployment_package(self) -> None:
        script = r'''
import sys, types, json
class StartTaskMessage: pass
class TaskContext: pass
sdk = types.ModuleType("blocks_network")
sdk.StartTaskMessage = StartTaskMessage
sdk.TaskContext = TaskContext
sys.modules["blocks_network"] = sdk
sys.path.insert(0, ".")
from handler import handler
class Part:
    def __init__(self, text): self.text = text
class Task:
    request_parts = [Part(json.dumps({"question": "smoke", "symbol": "BTC", "source_file": "yield_data.csv"}))]
result = handler(Task())
artifact = result["artifacts"][0]
assert artifact["mimeType"] == "application/json"
payload = json.loads(artifact["data"])
assert payload["agent"] == "crypto_risk_analyst"
assert payload["findings"]
assert payload["data_quality"]["missing_numeric_values"] == "null"
'''
        result = run_python("-c", script, cwd=DEPLOYMENT)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_deployment_metadata_is_card_derived(self) -> None:
        metadata = json.loads((DEPLOYMENT / "deployment-metadata.json").read_text(encoding="utf-8"))
        card = json.loads((DEPLOYMENT / "agent-card.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["agent_name"], card["identity"]["agentName"])
        self.assertEqual(metadata["card_contract"]["identity"]["agentName"], card["identity"]["agentName"])
        self.assertFalse(metadata["blocks_validation"]["executed_by_generator"])

    def test_guarded_trigger_never_dispatches_by_default(self) -> None:
        result = run_python("trigger_guarded.py", "--agent", "crypto_risk_analyst", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("not dispatched", result.stdout)

    def test_guarded_trigger_requires_paid_acknowledgement(self) -> None:
        result = run_python("trigger_guarded.py", "--agent", "crypto_risk_analyst", "--live")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--confirm-paid", result.stderr + result.stdout)

    def test_live_trigger_requires_key_before_sdk_import(self) -> None:
        script = "import os; os.environ.pop('BLOCKS_API_KEY', None); from trigger_guarded import live_trigger; live_trigger('crypto_risk_analyst', {'question': 'x'}, 1)"
        result = run_python("-c", script)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKS_API_KEY is required", result.stderr + result.stdout)

    def test_live_trigger_rejects_non_completed_terminal_state(self) -> None:
        from trigger_guarded import live_trigger
        os.environ["BLOCKS_API_KEY"] = "test-blocks-key"

        class Session:
            def on_progress(self, callback): pass
            def on_artifact(self, callback): pass
            def on_terminal(self, callback): self.callback = callback
            def close(self): pass
            def cancel(self): pass

        class Client:
            def send_message(self, **kwargs):
                session = Session()
                class Event: state = "failed"
                # The utility registers the callback before waiting; invoke it
                # from a short timer-like worker so the test remains local.
                import threading
                threading.Timer(0.01, lambda: session.callback(Event())).start()
                return session
            def destroy(self): pass

        with self.assertRaises(RuntimeError):
            live_trigger("crypto_risk_analyst", {"question": "test"}, 1, client_factory=lambda *args, **kwargs: Client())
        os.environ.pop("BLOCKS_API_KEY", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
