import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

from src.live.canary import fixture_opener, run_provider_canary
from src.live.collector import LiveDataCollector, is_fresh, load_symbols, validate_provider_url
from src.live.worker import merge_with_previous


def test_load_symbols_matches_canonical():
    symbols = load_symbols()
    assert len(symbols) == 59
    assert "BTC" in symbols
    assert symbols == sorted(symbols)


def test_collector_parses_injected_provider_payloads():
    responses = {
        "/api/v3/ticker/24hr": [{"symbol": "BTCUSDT", "lastPrice": "100", "priceChangePercent": "2.5", "quoteVolume": "1234"}],
        "/products/BTC-USD/stats": {"last": "101", "volume": "12"},
        "/products/ETH-USD/stats": {"last": "201", "volume": "13"},
        "/products/SOL-USD/stats": {"last": "51", "volume": "14"},
        "/v2/chains": [{"name": "Ethereum", "tvl": 123}],
    }

    class Response:
        status = 200
        headers = {"X-RateLimit-Remaining": "99"}
        def __init__(self, payload):
            self.payload = payload
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def getcode(self):
            return self.status
        def read(self):
            return json.dumps(self.payload).encode()

    def opener(request, timeout):
        path = urlparse(request.full_url).path
        if request.get_method() == "POST":
            body = json.loads(request.data.decode())
            if body["method"] == "eth_blockNumber":
                return Response({"result": "0x10"})
            return Response({"result": {"absoluteSlot": 20}})
        return Response(responses[path])

    collector = LiveDataCollector(["BTC", "ETH", "SOL"], timeout=1, opener=opener)
    for client in [collector.binance, collector.coinbase, collector.defillama, *collector.rpc.values()]:
        client.state.min_interval = 0
    snapshot = collector.collect()
    assert snapshot["market"]["assets"]["BTC"]["price_usd"] == 100
    assert snapshot["market"]["assets"]["BTC"]["secondary_price_usd"] == 101
    assert snapshot["defi"]["chains"][0]["tvl_usd"] == 123
    assert snapshot["blockchain"]["observations"]
    assert snapshot["provider_status"][0]["last_http_status"] == 200
    assert snapshot["provider_status"][0]["rate_limit_headers"]["x-ratelimit-remaining"] == "99"
    assert snapshot["errors"] == []


def test_provider_canary_fixture_captures_evidence():
    from src.live.canary import default_specs
    evidence = run_provider_canary(default_specs(), opener=fixture_opener)
    assert evidence["summary"] == {"providers": 5, "http_successes": 5, "schema_valid": 5, "errors": 0}
    assert all(item["request_started_at"] and item["request_finished_at"] for item in evidence["results"])
    assert all(item["latency_ms"] is not None for item in evidence["results"])
    assert all(item["response_headers"] for item in evidence["results"])


def test_provider_urls_reject_insecure_or_credentialed_values():
    assert validate_provider_url("https://example.com", "provider") == "https://example.com"
    for value in ("http://example.com", "https://user:pass@example.com"):
        try:
            validate_provider_url(value, "provider")
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe provider URL was accepted: {value}")


def test_merge_retains_previous_market_with_consistent_count():
    previous = {
        "generated_at": "2026-08-07T00:00:00Z",
        "market": {"assets": {"BTC": {"price_usd": 100, "observed_at": "2026-08-07T00:00:00Z"}}, "asset_count": 1},
        "defi": {"chains": [], "chain_count": 0},
        "blockchain": {"observations": [], "observation_count": 0},
    }
    current = {
        "generated_at": "2026-08-07T00:05:00Z",
        "market": {"assets": {}, "asset_count": 0},
        "defi": {"chains": [], "chain_count": 0},
        "blockchain": {"observations": [], "observation_count": 0},
        "errors": [{"provider": "binance", "error": "timeout"}],
    }
    merged = merge_with_previous(previous, current)
    assert merged["market"]["asset_count"] == 1
    assert merged["market"]["assets"]["BTC"]["observation_status"] == "retained_from_previous_cycle"
    assert merged["data_status"] == "live_overlay_degraded"


def test_freshness_rejects_stale_or_malformed_snapshots():
    assert is_fresh({"generated_at": "2026-08-07T00:00:00Z", "freshness": {"stale_after_seconds": 60}}, now=1786060861) is False
    assert is_fresh({"generated_at": "not-a-date"}) is False
