"""Run the live overlay tests with only the Python standard library."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_data import (
    test_collector_parses_injected_provider_payloads,
    test_freshness_rejects_stale_or_malformed_snapshots,
    test_load_symbols_matches_canonical,
    test_provider_urls_reject_insecure_or_credentialed_values,
    test_merge_retains_previous_market_with_consistent_count,
)

for test in (
    test_load_symbols_matches_canonical,
    test_collector_parses_injected_provider_payloads,
    test_provider_urls_reject_insecure_or_credentialed_values,
    test_merge_retains_previous_market_with_consistent_count,
    test_freshness_rejects_stale_or_malformed_snapshots,
):
    test()
    print(f"{test.__name__}: PASS")
