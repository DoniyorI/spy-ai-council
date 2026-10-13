import os
import sys

from src.engine.exit_manager import check_all_positions
from src.db import repository as repo
from src.utils.market_hours import is_trading_day, is_market_open
from src.utils.logging_config import log


def main():
    if os.path.exists("KILL_SWITCH"):
        log.warning("KILL_SWITCH present — aborting monitor")
        return

    if not is_trading_day():
        return

    if not is_market_open():
        return

    force_scalp = "--force-scalp-close" in sys.argv
    log.info(f"Position monitor running (force_scalp={force_scalp})")

    actions = check_all_positions(db_repo=repo, force_scalp_close=force_scalp)

    if actions:
        for a in actions:
            log.info(f"  {a['symbol']}: {a['reason']} pnl={a['pnl_pct']:.1f}% closed={a['closed']}")
    else:
        log.debug("No exit actions triggered")


if __name__ == "__main__":
    main()
