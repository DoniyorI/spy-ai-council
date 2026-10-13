import asyncio
import sys

from src.db import repository as repo
from src.jobs.morning_scan import _run
from src.utils.logging_config import log


def main():
    today_trades = repo.count_today_trades()
    if today_trades >= 2:
        log.info(f"Midday scan: daily cap reached ({today_trades}/2) — skip")
        return

    dry_run = "--dry-run" in sys.argv
    asyncio.run(_run(scan_type="midday", dry_run=dry_run))


if __name__ == "__main__":
    main()
