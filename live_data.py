"""Live market/blockchain overlay for Crypto Yield Matrix.

This module deliberately does not modify or replace ``yield_data.csv``.  It
collects current observations into a separate JSON snapshot.  Network access
is injected into ``LiveDataCollector`` so tests can run without the internet.
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / "yield_data.csv"
DEFAULT_OUTPUT = ROOT / "live_data" / "live_snapshot.json"
DEFAULT_STATUS = ROOT / "live_data" / "worker_status.json"
USER_AGENT = "CryptoYieldMatrixLiveWorker/1.0 (+https://github.com/)"

# Conservative polling intervals. The worker performs one cycle per interval,
# while each provider has its own minimum request spacing and retry policy.
DEFAULT_CYCLE_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_STALE_AFTER_SECONDS = 900

BINANCE_SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "MATIC": "MATICUSDT", "ADA": "ADAUSDT", "XRP": "XRPUSDT", "AVAX": "AVAXUSDT", "DOT": "DOTUSDT", "ATOM": "ATOMUSDT", "LINK": "LINKUSDT", "AAVE": "AAVEUSDT", "UNI": "UNIUSDT", "ARB": "ARBUSDT", "OP": "OPUSDT", "NEAR": "NEARUSDT", "SEI": "SEIUSDT", "TIA": "TIAUSDT", "INJ": "INJUSDT", "FIL": "FILUSDT", "ALGO": "ALGOUSDT", "TRX": "TRXUSDT", "XLM": "XLMUSDT", "EOS": "EOSUSDT", "NEO": "NEOUSDT", "VET": "VETUSDT", "THETA": "THETAUSDT", "FTM": "FTMUSDT", "ONE": "ONEUSDT", "KAVA": "KAVAUSDT", "ROSE": "ROSEUSDT", "FLOW": "FLOWUSDT", "MINA": "MINAUSDT", "CELO": "CELOUSDT", "GLMR": "GLMRUSDT", "PENDLE": "PENDLEUSDT", "EIGEN": "EIGENUSDT", "ETHFI": "ETHFIUSDT", "JTO": "JTOUSDT", "LDO": "LDOUSDT", "RPL": "RPLUSDT", "MNDE": "MNDEUSDT", "HYPE": "HYPEUSDT", "ONDO": "ONDOUSDT", "ICP": "ICPUSDT", "GRT": "GRTUSDT", "CRO": "CROUSDT", "MKR": "MKRUSDT", "CRV": "CRVUSDT", "SNX": "SNXUSDT", "COMP": "COMPUSDT", "BAL": "BALUSDT", "YFI": "YFIUSDT", "WLD": "WLDUSDT", "LUNC": "LUNCUSDT"}
COINBASE_PRODUCTS = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "MATIC": "MATIC-USD", "ADA": "ADA-USD", "XRP": "XRP-USD"}

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_symbols(path: Path = CANONICAL) -> list[str]:
    import csv
    with path.open(encoding="utf-8-sig", newline="") as handle:
        symbols = sorted({row.get("symbol", "").strip().upper() for row in csv.DictReader(handle) if row.get("symbol")})
    if not symbols:
        raise ValueError(f"no asset symbols found in {path}")
    return symbols

def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if parsed == parsed and abs(parsed) != float("inf") else None
    except (TypeError, ValueError):
        return None

@dataclass
class ProviderState:
    name: str
    min_interval: float
    last_request: float = 0.0
    failures: int = 0
    last_error: str | None = None
    last_success: str | None = None

    def wait(self, sleep: Callable[[float], None] = time.sleep) -> None:
        delay = self.min_interval - (time.monotonic() - self.last_request)
        if delay > 0:
            sleep(delay)
        self.last_request = time.monotonic()

class ProviderClient:
    def __init__(self, name: str, base_url: str, min_interval: float, timeout: float = DEFAULT_TIMEOUT_SECONDS, opener: Callable[..., Any] | None = None) -> None:
        self.state = ProviderState(name, min_interval)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.opener = opener or urlopen

    def get_json(self, path: str, headers: dict[str, str] | None = None, attempts: int = 2) -> Any:
        last_error: Exception | None = None
        for attempt in range(attempts):
            self.state.wait()
            request = Request(self.base_url + path, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    value = json.loads(response.read().decode("utf-8"))
                self.state.failures = 0
                self.state.last_error = None
                self.state.last_success = iso_now()
                return value
            except HTTPError as error:
                last_error = error
                self.state.last_error = f"HTTP {error.code}"
                if error.code not in (408, 425, 429, 500, 502, 503, 504):
                    break
            except (URLError, TimeoutError, OSError, ValueError) as error:
                last_error = error
                self.state.last_error = str(error)[:240]
            self.state.failures += 1
            if attempt + 1 < attempts:
                time.sleep(min(30.0, (2 ** attempt) + random.random()))
        raise RuntimeError(f"{self.state.name} request failed: {last_error}")

class LiveDataCollector:
    """Collect one best-effort cycle; failures never erase the previous snapshot."""
    def __init__(self, symbols: list[str], timeout: float = DEFAULT_TIMEOUT_SECONDS, opener: Callable[..., Any] | None = None) -> None:
        self.symbols = symbols
        self.binance = ProviderClient("binance", os.getenv("BINANCE_API_URL", "https://api.binance.com"), 1.0, timeout, opener)
        self.coinbase = ProviderClient("coinbase", os.getenv("COINBASE_API_URL", "https://api.exchange.coinbase.com"), 1.0, timeout, opener)
        self.defillama = ProviderClient("defillama", os.getenv("DEFILLAMA_API_URL", "https://api.llama.fi"), 2.0, timeout, opener)
        self.rpc = {
            "ethereum": ProviderClient("ethereum_rpc", os.getenv("ETHEREUM_RPC_URL", "https://cloudflare-eth.com"), 2.0, timeout, opener),
            "solana": ProviderClient("solana_rpc", os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"), 2.0, timeout, opener),
        }

    def _market(self) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        observations: dict[str, dict[str, Any]] = {}
        errors: list[dict[str, Any]] = []
        try:
            rows = self.binance.get_json("/api/v3/ticker/24hr")
            by_symbol = {row.get("symbol"): row for row in rows if isinstance(row, dict)}
            observed = iso_now()
            for asset in self.symbols:
                row = by_symbol.get(BINANCE_SYMBOLS.get(asset))
                if not row:
                    continue
                observations[asset] = {"price_usd": _number(row.get("lastPrice")), "change_24h_pct": _number(row.get("priceChangePercent")), "volume_24h_usd": _number(row.get("quoteVolume")), "provider": "binance", "endpoint": "/api/v3/ticker/24hr", "observed_at": observed}
        except Exception as error:
            errors.append({"provider": "binance", "error": str(error)[:240]})
        # A small independent secondary sample makes provider drift visible and
        # provides fallback prices without making one request per asset.
        for asset in ("BTC", "ETH", "SOL"):
            if asset not in self.symbols:
                continue
            try:
                row = self.coinbase.get_json(f"/products/{quote(COINBASE_PRODUCTS[asset])}/stats")
                if asset not in observations and row.get("last") is not None:
                    observations[asset] = {"price_usd": _number(row.get("last")), "volume_24h_usd": _number(row.get("volume")), "provider": "coinbase", "endpoint": "/products/<product>/stats", "observed_at": iso_now()}
                elif asset in observations:
                    observations[asset]["secondary_price_usd"] = _number(row.get("last"))
                    observations[asset]["secondary_provider"] = "coinbase"
            except Exception as error:
                errors.append({"provider": "coinbase", "asset": asset, "error": str(error)[:240]})
        return observations, errors

    def _defi(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            chains = self.defillama.get_json("/v2/chains")
            wanted = {"ethereum", "solana", "arbitrum", "optimism", "polygon", "avalanche", "cosmos", "near", "sui", "aptos"}
            result = []
            for row in chains if isinstance(chains, list) else []:
                name = str(row.get("name", "")).lower()
                if name in wanted:
                    result.append({"chain": row.get("name"), "tvl_usd": _number(row.get("tvl")), "provider": "defillama", "endpoint": "/v2/chains", "observed_at": iso_now()})
            return result, []
        except Exception as error:
            return [], [{"provider": "defillama", "error": str(error)[:240]}]

    def _blockchain(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        result: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        calls = {"ethereum": {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}, "solana": {"jsonrpc": "2.0", "method": "getEpochInfo", "params": [], "id": 1}}
        for chain, client in self.rpc.items():
            try:
                # JSON-RPC providers require POST; use the same guarded opener
                # and provider limiter, with no retries on malformed results.
                client.state.wait()
                request = Request(client.base_url, data=json.dumps(calls[chain]).encode(), headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"}, method="POST")
                with client.opener(request, timeout=client.timeout) as response:
                    payload = json.loads(response.read().decode())
                value = payload.get("result") if isinstance(payload, dict) else None
                if chain == "ethereum" and isinstance(value, str):
                    value = int(value, 16)
                height = value.get("absoluteSlot") if chain == "solana" and isinstance(value, dict) else value
                if height is not None:
                    result.append({"chain": chain, "block_height": height, "provider": client.state.name, "endpoint": client.base_url, "observed_at": iso_now()})
                client.state.last_error = None
                client.state.last_success = iso_now()
            except Exception as error:
                client.state.failures += 1
                client.state.last_error = str(error)[:240]
                errors.append({"provider": client.state.name, "error": str(error)[:240]})
        return result, errors

    def collect(self) -> dict[str, Any]:
        market, market_errors = self._market()
        chains, chain_errors = self._defi()
        blockchain, rpc_errors = self._blockchain()
        now = iso_now()
        states = [self.binance.state, self.coinbase.state, self.defillama.state, *self.rpc.values()]
        return {"schema_version": "live-overlay-1", "generated_at": now, "canonical_source": "yield_data.csv", "data_status": "live_overlay_only", "freshness": {"stale_after_seconds": DEFAULT_STALE_AFTER_SECONDS, "generated_at": now}, "market": {"assets": market, "asset_count": len(market)}, "defi": {"chains": chains, "chain_count": len(chains)}, "blockchain": {"observations": blockchain, "observation_count": len(blockchain)}, "provider_status": [{"provider": state.name, "last_success": state.last_success, "last_error": state.last_error, "failures": state.failures} for state in states], "errors": market_errors + chain_errors + rpc_errors}

def write_snapshot(snapshot: dict[str, Any], output: Path = DEFAULT_OUTPUT) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)

def is_fresh(snapshot: dict[str, Any], now: float | None = None) -> bool:
    try:
        generated = datetime.fromisoformat(snapshot["generated_at"].replace("Z", "+00:00")).timestamp()
        return (time.time() if now is None else now) - generated <= float(snapshot.get("freshness", {}).get("stale_after_seconds", DEFAULT_STALE_AFTER_SECONDS))
    except (KeyError, TypeError, ValueError):
        return False
