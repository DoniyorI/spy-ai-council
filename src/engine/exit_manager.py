from datetime import date

from config.settings import TRADE_TYPE_CONFIG
from src.brokers.alpaca_client import get_positions, submit_option_order, wait_for_fill, cancel_order
from src.utils.market_hours import is_within_n_min_of_close, trading_days_between
from src.utils.time_helpers import today_et
from src.utils.logging_config import log


def _close_position(pos: dict, reason: str, db_repo=None) -> bool:
    symbol = pos["symbol"]
    qty = int(abs(pos["qty"]))
    mid = pos.get("current_price") or pos.get("avg_entry_price")

    if not mid:
        log.warning(f"No price for {symbol}, cannot close")
        return False

    log.info(f"Closing {symbol} qty={qty} reason={reason}")
    try:
        order = submit_option_order(symbol, qty, "SELL", round(float(mid), 2))
        filled = wait_for_fill(order["id"], timeout=60)

        if not filled:
            # Aggressive fallback: sell at bid
            bid = pos.get("bid", float(mid) * 0.95)
            order2 = submit_option_order(symbol, qty, "SELL", round(float(bid), 2))
            filled = wait_for_fill(order2["id"], timeout=30)
            if not filled:
                cancel_order(order2["id"])
                log.error(f"Could not close {symbol}")
                return False

        if db_repo:
            db_repo.update_trade_close(
                contract_symbol=symbol,
                exit_fill_price=filled["filled_avg_price"],
                exit_reason=reason,
            )
        log.info(f"Closed {symbol} @ {filled['filled_avg_price']} reason={reason}")
        return True
    except Exception as e:
        log.error(f"Error closing {symbol}: {e}")
        return False


def check_all_positions(db_repo=None, force_scalp_close: bool = False) -> list[dict]:
    positions = get_positions()
    actions = []

    for pos in positions:
        if not pos.get("is_option"):
            continue

        symbol = pos["symbol"]
        entry_price = float(pos["avg_entry_price"])
        qty = float(pos["qty"])
        market_val = float(pos["market_value"])
        current_price = market_val / (qty * 100) if qty else entry_price

        trade_record = db_repo.get_open_trade_by_symbol(symbol) if db_repo else None
        trade_type = trade_record.get("trade_type", "SHORT_SWING") if trade_record else "SHORT_SWING"
        cfg = TRADE_TYPE_CONFIG.get(trade_type, TRADE_TYPE_CONFIG["SHORT_SWING"])

        entry_total = entry_price * qty * 100
        pnl_pct = (market_val - entry_total) / entry_total * 100 if entry_total else 0

        entry_time = trade_record.get("entry_time") if trade_record else None
        days_held = trading_days_between(entry_time, today_et()) if entry_time else 0

        exp_date = trade_record.get("expiration") if trade_record else None
        dte_left = (date.fromisoformat(exp_date) - today_et()).days if exp_date else 999

        reason = None

        if pnl_pct >= cfg["take_profit_pct"]:
            reason = "take_profit"
        elif pnl_pct <= -cfg["stop_loss_pct"]:
            reason = "stop_loss"
        elif days_held >= cfg["max_hold_days"]:
            reason = "time_stop"
        elif dte_left <= cfg["dte_force_exit"]:
            reason = "dte_force_exit"
        elif trade_type == "SCALP" and is_within_n_min_of_close(15):
            reason = "scalp_eod_close"
        elif force_scalp_close and trade_type == "SCALP":
            reason = "scalp_forced_close"

        if reason:
            pos["current_price"] = current_price
            closed = _close_position(pos, reason, db_repo)
            actions.append({"symbol": symbol, "reason": reason, "closed": closed, "pnl_pct": pnl_pct})
            log.info(f"Exit action: {symbol} {reason} pnl={pnl_pct:.1f}%")
        else:
            log.debug(f"Hold {symbol}: pnl={pnl_pct:.1f}% days={days_held} dte={dte_left}")

    return actions
