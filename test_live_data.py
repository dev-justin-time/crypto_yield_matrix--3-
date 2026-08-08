import json
from pathlib import Path

from live_data import LiveDataCollector, is_fresh, load_symbols


def test_load_symbols_matches_canonical():
    symbols = load_symbols()
    assert len(symbols) == 59
    assert "BTC" in symbols
    assert symbols == sorted(symbols)


def test_collector_parses_injected_provider_payloads(monkeypatch):
    responses = {
        "/api/v3/ticker/24hr": [{"symbol": "BTCUSDT", "lastPrice": "100", "priceChangePercent": "2.5", "quoteVolume": "1234"}],
        "/products/BTC-USD/stats": {"last": "101", "volume": "12"},
        "/products/ETH-USD/stats": {"last": "201", "volume": "13"},
        "/products/SOL-USD/stats": {"last": "51", "volume": "14"},
        "/v2/chains": [{"name": "Ethereum", "tvl": 123}],
    }

    class Response:
        def __init__(self, payload):
            self.payload = payload
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps(self.payload).encode()

    def opener(request, timeout):
        path = request.full_url.split(".com", 1)[-1]
        if request.method == "POST":
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
    assert snapshot["errors"] == []


def test_freshness_rejects_stale_or_malformed_snapshots():
    assert is_fresh({"generated_at": "2026-08-07T00:00:00Z", "freshness": {"stale_after_seconds": 60}}, now=1786060830) is False
    assert is_fresh({"generated_at": "not-a-date"}) is False
