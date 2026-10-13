import asyncio
import json
import os
import sys

from src.data.context_builder import build_context
from src.data.options_data import fetch_chain, compute_greeks_if_missing
from src.ai.prompt_runner import run_council
from src.engine.voting import decide
from src.engine.risk_rules import evaluate
from src.engine.contract_selector import select
from src.engine.trade_executor import execute
from src.brokers.alpaca_client import get_account, get_positions
from src.db import repository as repo
from src.utils.market_hours import is_trading_day, is_market_open
from src.utils.time_helpers import today_et
from src.utils.logging_config import log


async def _run(scan_type: str = "morning", dry_run: bool = False):
    if os.path.exists("KILL_SWITCH"):
        log.warning("KILL_SWITCH present — aborting scan")
        return

    if not is_trading_day():
        log.info("Not a trading day — skipping scan")
        return

    if not is_market_open(buffer_min=4):
        log.info("Market not open yet — skipping scan")
        return

    log.info(f"=== {scan_type.upper()} SCAN starting ===")

    account = get_account()
    positions = get_positions()
    today_trades = repo.count_today_trades()

    if today_trades >= 2:
        log.info(f"Daily trade cap reached ({today_trades}/2) — no scan needed")
        return

    context = build_context()
    context["account"]["open_positions"] = len([p for p in positions if p["is_option"]])
    context["account"]["trades_today"] = today_trades

    scan_id = repo.log_scan(context, scan_type)
    log.info(f"Scan logged: id={scan_id}")

    council_results = await run_council(context)

    # Log all AI outputs
    for r in council_results.raw_results:
        parsed_data = r.parsed.model_dump() if r.parsed else {}
        repo.log_ai_output(
            scan_id=scan_id,
            model=r.model_name,
            prompt_name=r.prompt_name,
            raw_output=r.raw_text,
            parsed=parsed_data,
            latency_ms=r.latency_ms,
        )

    decision = decide(council_results.p1_p3_outputs, council_results.p4_outputs)
    log.info(f"Decision: {decision.action} type={decision.trade_type} conf={decision.confidence}")

    # Fetch fresh chain for contract selection
    chain = fetch_chain(min_dte=1, max_dte=45)
    spot = context["spot"]["last"]
    if not chain.empty and spot:
        chain = compute_greeks_if_missing(chain, spot)

    selected_contract = None
    if decision.action != "NO_TRADE" and decision.trade_type and not chain.empty:
        selected_contract = select(
            decision.action,
            chain,
            decision.trade_type,
            decision.preferred_symbol,
        )

    contract_cost = selected_contract["mid"] * 100 if selected_contract else None
    today_pnl_pct = 0.0  # TODO: pull from realized PnL for today

    risk = evaluate(
        decision=decision,
        account=account,
        positions=positions,
        today_trades=today_trades,
        today_realized_pnl_pct=today_pnl_pct,
        contract_cost_usd=contract_cost,
    )

    decision_id = repo.log_decision(
        scan_id=scan_id,
        final_action=decision.action,
        trade_type=decision.trade_type,
        confidence=decision.confidence,
        vote_breakdown=decision.vote_breakdown or {},
        risk_result="APPROVE" if risk.approved else "BLOCK",
        risk_reason=None if risk.approved else risk.reason,
        selected_contract=selected_contract["symbol"] if selected_contract else None,
    )

    if not risk.approved:
        log.info(f"Risk gate BLOCKED: {risk.reason}")
        return

    if selected_contract is None:
        log.warning("No valid contract found — skipping trade")
        return

    filled = execute(decision, selected_contract, dry_run=dry_run)
    if filled:
        repo.log_trade(decision_id, filled, selected_contract, decision.trade_type)
        log.info(
            f"Trade placed: {filled['symbol']} @ {filled.get('filled_avg_price')} "
            f"type={decision.trade_type}"
        )
    else:
        log.warning("Trade execution failed or dry-run")

    log.info(f"=== {scan_type.upper()} SCAN complete ===")


def main():
    dry_run = "--dry-run" in sys.argv
    asyncio.run(_run(scan_type="morning", dry_run=dry_run))


if __name__ == "__main__":
    main()
