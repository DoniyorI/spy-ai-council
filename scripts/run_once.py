"""Run the full pipeline once. --dry-run skips actual order submission."""
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.jobs.morning_scan import _run


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    if force:
        with patch("src.jobs.morning_scan.is_market_open", return_value=True), \
             patch("src.jobs.morning_scan.is_trading_day", return_value=True), \
             patch("src.engine.risk_rules.is_market_open", return_value=True), \
             patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False):
            asyncio.run(_run(scan_type="manual", dry_run=dry_run))
    else:
        asyncio.run(_run(scan_type="manual", dry_run=dry_run))


if __name__ == "__main__":
    main()
