"""Controlled provider-canary evidence utility.

The default command uses deterministic fixtures and never contacts a provider.
A real run requires both ``--live`` and ``--confirm-live``. The live command is
intended for an operator-controlled, terms-reviewed canary and writes a JSON
evidence record; it is not part of paid task execution.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from live_data import validate_provider_url

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "live_data" / "provider_canary_evidence.json"
CANARY_SCHEMA_VERSION = "live-provider-canary-1"
SAFE_HEADER_NAMES = {
    "retry-after",
    "x-rate-limit-limit",
    "x-rate-limit-remaining",
    "x-rate-limit-reset",
    "x-mbx-used-weight",
    "x-mbx-used-weight-1m",
    "x-mbx-used-weight-1s",
    "x-mbx-used-weight-1h",
    "x-mbx-used-weight-1d",
    "ratelimit-limit",
    "ratelimit-remaining",
    "ratelimit-reset",
    "cf-ray",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_url(value: str) -> str:
    """Return a URL without query credentials or fragments."""
    parsed = urlparse(value)
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return parsed._replace(netloc=host, query="", fragment="").geturl()


def safe_error(error: BaseException) -> str:
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, URLError):
        return f"URLError: {type(error.reason).__name__}"
    return f"{type(error).__name__}: request failed"


def capture_headers(headers: Any) -> dict[str, str]:
    captured: dict[str, str] = {}
    for key, value in headers.items() if headers is not None else ():
        normalized = str(key).lower()
        if normalized in SAFE_HEADER_NAMES or "rate" in normalized or "retry" in normalized:
            captured[normalized] = str(value)[:200]
    return captured


def schema_result(payload: Any, schema: str) -> dict[str, Any]:
    if schema == "binance_ticker":
        valid = isinstance(payload, list) and bool(payload) and all(
            isinstance(row, dict) and isinstance(row.get("symbol"), str) and "lastPrice" in row
            for row in payload
        )
        reason = "list of ticker rows with symbol and lastPrice" if valid else "expected non-empty ticker list"
    elif schema == "coinbase_stats":
        valid = isinstance(payload, dict) and payload.get("last") is not None
        reason = "stats object with last" if valid else "expected stats object with last"
    elif schema == "defillama_chains":
        valid = isinstance(payload, list) and all(isinstance(row, dict) and "name" in row for row in payload)
        reason = "chain list with name fields" if valid else "expected chain list with name fields"
    elif schema == "ethereum_rpc":
        valid = isinstance(payload, dict) and payload.get("jsonrpc") == "2.0" and "result" in payload
        reason = "JSON-RPC 2.0 result object" if valid else "expected JSON-RPC 2.0 result object"
    elif schema == "solana_rpc":
        valid = isinstance(payload, dict) and payload.get("jsonrpc") == "2.0" and isinstance(payload.get("result"), dict)
        reason = "JSON-RPC 2.0 object result" if valid else "expected JSON-RPC 2.0 object result"
    else:
        raise ValueError(f"unknown canary schema '{schema}'")
    return {"valid": valid, "description": reason}


@dataclass(frozen=True)
class CanarySpec:
    provider: str
    url: str
    schema: str
    method: str = "GET"
    body: dict[str, Any] | None = None
    endpoint: str = ""


def default_specs() -> list[CanarySpec]:
    values = {
        "binance": os.getenv("BINANCE_API_URL", "https://api.binance.com"),
        "coinbase": os.getenv("COINBASE_API_URL", "https://api.exchange.coinbase.com"),
        "defillama": os.getenv("DEFILLAMA_API_URL", "https://api.llama.fi"),
        "ethereum_rpc": os.getenv("ETHEREUM_RPC_URL", "https://cloudflare-eth.com"),
        "solana_rpc": os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
    }
    return [
        CanarySpec("binance", validate_provider_url(values["binance"], "BINANCE_API_URL") + "/api/v3/ticker/24hr", "binance_ticker", endpoint="/api/v3/ticker/24hr"),
        CanarySpec("coinbase", validate_provider_url(values["coinbase"], "COINBASE_API_URL") + "/products/BTC-USD/stats", "coinbase_stats", endpoint="/products/BTC-USD/stats"),
        CanarySpec("defillama", validate_provider_url(values["defillama"], "DEFILLAMA_API_URL") + "/v2/chains", "defillama_chains", endpoint="/v2/chains"),
        CanarySpec("ethereum_rpc", validate_provider_url(values["ethereum_rpc"], "ETHEREUM_RPC_URL"), "ethereum_rpc", method="POST", body={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}, endpoint="/ (eth_blockNumber)"),
        CanarySpec("solana_rpc", validate_provider_url(values["solana_rpc"], "SOLANA_RPC_URL"), "solana_rpc", method="POST", body={"jsonrpc": "2.0", "method": "getEpochInfo", "params": [], "id": 1}, endpoint="/ (getEpochInfo)"),
    ]


def run_provider_canary(
    specs: list[CanarySpec],
    opener: Callable[..., Any] = urlopen,
    timeout: float = 15.0,
) -> dict[str, Any]:
    started = utc_now()
    results: list[dict[str, Any]] = []
    for spec in specs:
        request_started = utc_now()
        timer = time.perf_counter_ns()
        result: dict[str, Any] = {
            "provider": spec.provider,
            "method": spec.method,
            "endpoint": spec.endpoint,
            "url": safe_url(spec.url),
            "request_started_at": request_started,
            "request_finished_at": None,
            "latency_ms": None,
            "http_status": None,
            "response_headers": {},
            "schema": {"valid": False, "description": "not evaluated"},
            "error": None,
        }
        body = json.dumps(spec.body).encode("utf-8") if spec.body is not None else None
        headers = {"User-Agent": "CryptoYieldMatrixProviderCanary/1.0", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(spec.url, data=body, headers=headers, method=spec.method)
        try:
            with opener(request, timeout=timeout) as response:
                result["http_status"] = int(getattr(response, "status", response.getcode()))
                result["response_headers"] = capture_headers(getattr(response, "headers", None))
                payload = json.loads(response.read().decode("utf-8"))
            result["schema"] = schema_result(payload, spec.schema)
            if not result["schema"]["valid"]:
                result["error"] = "response schema validation failed"
        except HTTPError as error:
            result["http_status"] = int(error.code)
            result["response_headers"] = capture_headers(error.headers)
            result["error"] = safe_error(error)
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as error:
            result["error"] = safe_error(error)
        finally:
            result["request_finished_at"] = utc_now()
            result["latency_ms"] = round((time.perf_counter_ns() - timer) / 1_000_000, 3)
        results.append(result)
    finished = utc_now()
    return {
        "schema_version": CANARY_SCHEMA_VERSION,
        "run_started_at": started,
        "run_finished_at": finished,
        "results": results,
        "summary": {
            "providers": len(results),
            "http_successes": sum(200 <= (item["http_status"] or 0) < 300 for item in results),
            "schema_valid": sum(bool(item["schema"]["valid"]) for item in results),
            "errors": sum(item["error"] is not None for item in results),
        },
        "policy": "Evidence only; does not modify yield_data.csv, dispatch Blocks tasks, or certify provider terms.",
    }


def write_evidence(evidence: dict[str, Any], output: Path = DEFAULT_OUTPUT) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)


def fixture_opener(request: Request, timeout: float) -> Any:
    """Return representative payloads for safe local schema testing."""
    class Response:
        status = 200
        headers = {"X-MBX-USED-WEIGHT-1M": "1", "X-RateLimit-Remaining": "99"}
        def __init__(self, payload: Any): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *_: Any) -> bool: return False
        def getcode(self) -> int: return self.status
        def read(self) -> bytes: return json.dumps(self.payload).encode("utf-8")
    if "ticker" in request.full_url:
        return Response([{"symbol": "BTCUSDT", "lastPrice": "100"}])
    if "products" in request.full_url:
        return Response({"last": "100"})
    if "chains" in request.full_url:
        return Response([{"name": "Ethereum", "tvl": 1}])
    body = json.loads((request.data or b"{}").decode("utf-8"))
    if body.get("method") == "eth_blockNumber":
        return Response({"jsonrpc": "2.0", "result": "0x10", "id": 1})
    return Response({"jsonrpc": "2.0", "result": {"absoluteSlot": 10}, "id": 1})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fixture", action="store_true", help="run deterministic local fixtures (default)")
    mode.add_argument("--live", action="store_true", help="call configured public/provider endpoints")
    parser.add_argument("--confirm-live", action="store_true", help="required with --live; confirms terms and rate-limit review")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.live and not args.confirm_live:
        parser.error("--live requires --confirm-live after an operator reviews provider terms and limits")
    if args.live:
        evidence = run_provider_canary(default_specs())
    else:
        evidence = run_provider_canary(default_specs(), opener=fixture_opener)
    write_evidence(evidence, args.output)
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["summary"]["errors"] == 0 and evidence["summary"]["schema_valid"] == evidence["summary"]["providers"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
