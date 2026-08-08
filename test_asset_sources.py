from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from blocks_agents.handlers import common
from blocks_agents.handlers.common import load_asset_snapshot, snapshot_research
from blocks_agents.handlers.crypto_risk_analyst import handler as risk_handler
from organize_csv_sources import MANIFEST, check

ROOT = Path(__file__).resolve().parent


class AssetSourceTests(unittest.TestCase):
    def test_named_source_manifest_is_complete(self):
        self.assertEqual(list((ROOT / "csv").glob("table-*.csv")), [])
        self.assertEqual(check(), 0)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["records"]), 15)
        self.assertTrue(all(item.get("original_sha256") == item.get("sha256") for item in manifest["records"]))
        self.assertEqual(sum(item["kind"] == "asset_snapshot" for item in manifest["records"]), 9)
        self.assertEqual(sum(item["kind"] == "reference" for item in manifest["records"]), 6)

    def test_asset_snapshot_loader_preserves_supplied_fields(self):
        row = load_asset_snapshot("LINK")
        self.assertEqual(row["symbol"], "LINK-USD")
        self.assertEqual(row["website"], "https://chain.link/")
        research = snapshot_research("LINK")
        self.assertEqual(research["status"], "source_snapshot")
        self.assertIsNotNone(research["price_usd"])
        self.assertEqual(research["source_file"], "csv/source_snapshots/LINK.csv")

    def test_handler_artifact_contains_named_snapshot_research(self):
        class Part:
            text = json.dumps({"question": "risk", "symbol": "LINK", "source_file": "yield_data.csv"})
        class Task:
            request_parts = [Part()]
        payload = json.loads(risk_handler(Task())["artifacts"][0]["data"])
        finding = payload["findings"][0]
        self.assertEqual(finding["market_snapshot_research"]["source_file"], "csv/source_snapshots/LINK.csv")
        self.assertEqual(finding["market_snapshot_research"]["status"], "source_snapshot")

    def test_uncovered_asset_is_explicitly_unavailable(self):
        research = snapshot_research("MATIC")
        self.assertEqual(research["status"], "unavailable")
        self.assertIsNone(research["price_usd"])
        self.assertTrue(research["research_use"])

    def test_filename_symbol_mismatch_is_not_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "LINK.csv"
            path.write_text("symbol,regularMarketPrice\nETH-USD,1\n", encoding="utf-8")
            original_dir = common.SOURCE_SNAPSHOT_DIR
            common.SOURCE_SNAPSHOT_DIR = Path(directory)
            try:
                self.assertEqual(load_asset_snapshot("LINK"), {})
            finally:
                common.SOURCE_SNAPSHOT_DIR = original_dir

    def test_each_named_snapshot_is_one_row_and_symbol_named(self):
        for path in sorted((ROOT / "csv/source_snapshots").glob("*.csv")):
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1, path)
            self.assertEqual(rows[0]["symbol"].removesuffix("-USD").upper(), path.stem)


if __name__ == "__main__":
    unittest.main(verbosity=2)
