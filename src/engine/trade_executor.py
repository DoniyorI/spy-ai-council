import os
from typing import Optional

from src.brokers.alpaca_client import submit_option_order, wait_for_fill, cancel_order
from src.engine.voting import Decision
from src.utils.logging_config import log


def execute(decision: Decision, contract: dict, dry_run: bool = False) -> Optional[dict]:
    symbol = contract["symbol"]
    mid = contract["mid"]
    limit_price = round(mid, 2)
    qty = 1

    log.info(
        f"{'[DRY RUN] ' if dry_run else ''}Placing BUY {symbol} "
        f"qty={qty} limit={limit_price} type={decision.trade_type}"
    )

    if dry_run or os.getenv("TRADING_MODE") == "dry_run":
        log.info("[DRY RUN] Order not submitted")
        return {
            "id": "dry-run-order",
            "symbol": symbol,
            "limit_price": limit_price,
            "filled_avg_price": limit_price,
            "filled_qty": qty,
            "status": "dry_run",
            "trade_type": decision.trade_type,
        }

    order = submit_option_order(symbol, qty, "BUY", limit_price)
    order_id = order["id"]

    filled = wait_for_fill(order_id, timeout=60)
    if filled:
        log.info(f"Order filled: {symbol} @ {filled['filled_avg_price']}")
        filled["trade_type"] = decision.trade_type
        return filled

    # Retry at a slightly better price (cross the spread once)
    log.warning(f"Not filled at mid {limit_price:.2f} — retrying at ask")
    retry_price = round(contract["ask"], 2)
    if retry_price > limit_price:
        order2 = submit_option_order(symbol, qty, "BUY", retry_price)
        filled2 = wait_for_fill(order2["id"], timeout=45)
        if filled2:
            log.info(f"Retry fill: {symbol} @ {filled2['filled_avg_price']}")
            filled2["trade_type"] = decision.trade_type
            return filled2
        cancel_order(order2["id"])

    log.error(f"Order for {symbol} could not be filled — skipping trade")
    return None
