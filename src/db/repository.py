import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from config.settings import DATABASE_URL
from src.db.models import Base, Scan, AIOutput, Decision, PaperTrade, DailyPerformance
from src.utils.logging_config import log

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        Path("data").mkdir(exist_ok=True)
        _engine = create_engine(DATABASE_URL, echo=False)
        Base.metadata.create_all(_engine)
    return _engine


def _session() -> Session:
    return Session(get_engine())


def log_scan(context: dict, scan_type: str = "morning") -> int:
    with _session() as s:
        scan = Scan(
            scan_time=datetime.utcnow(),
            scan_type=scan_type,
            context_json=json.dumps(context, default=str),
        )
        s.add(scan)
        s.commit()
        return scan.id


def log_ai_output(
    scan_id: int,
    model: str,
    prompt_name: str,
    raw_output: str,
    parsed: dict,
    latency_ms: int = 0,
) -> int:
    with _session() as s:
        row = AIOutput(
            scan_id=scan_id,
            model=model,
            prompt_name=prompt_name,
            raw_output=raw_output,
            parsed_json=json.dumps(parsed, default=str),
            direction=parsed.get("direction") or parsed.get("final_action"),
            confidence=parsed.get("confidence"),
            preferred_symbol=parsed.get("preferred_contract_symbol"),
            latency_ms=latency_ms,
        )
        s.add(row)
        s.commit()
        return row.id


def log_decision(
    scan_id: int,
    final_action: str,
    trade_type: Optional[str],
    confidence: float,
    vote_breakdown: dict,
    risk_result: str,
    risk_reason: Optional[str],
    selected_contract: Optional[str],
) -> int:
    with _session() as s:
        row = Decision(
            scan_id=scan_id,
            final_action=final_action,
            trade_type=trade_type,
            confidence=confidence,
            vote_breakdown_json=json.dumps(vote_breakdown, default=str),
            risk_gate_result=risk_result,
            risk_block_reason=risk_reason,
            selected_contract=selected_contract,
        )
        s.add(row)
        s.commit()
        return row.id


def log_trade(
    decision_id: int,
    order: dict,
    contract: dict,
    trade_type: str,
) -> int:
    with _session() as s:
        row = PaperTrade(
            decision_id=decision_id,
            alpaca_order_id=order["id"],
            contract_symbol=order["symbol"],
            trade_type=trade_type,
            side="buy",
            qty=int(order.get("filled_qty", 1)),
            entry_limit_price=order.get("limit_price"),
            entry_fill_price=order.get("filled_avg_price"),
            entry_time=datetime.utcnow(),
            expiration=str(contract.get("expiration", "")),
            status="open",
        )
        s.add(row)
        s.commit()
        return row.id


def update_trade_close(
    contract_symbol: str,
    exit_fill_price: float,
    exit_reason: str,
) -> None:
    with _session() as s:
        stmt = (
            select(PaperTrade)
            .where(PaperTrade.contract_symbol == contract_symbol)
            .where(PaperTrade.status == "open")
        )
        trade = s.scalars(stmt).first()
        if not trade:
            log.warning(f"No open trade found for {contract_symbol}")
            return

        trade.exit_fill_price = exit_fill_price
        trade.exit_time = datetime.utcnow()
        trade.exit_reason = exit_reason
        trade.status = "closed"

        if trade.entry_fill_price:
            cost = trade.entry_fill_price * trade.qty * 100
            pnl = (exit_fill_price - trade.entry_fill_price) * trade.qty * 100
            trade.realized_pnl = round(pnl, 2)
            trade.realized_pnl_pct = round(pnl / cost * 100, 2) if cost else 0
            if trade.entry_time:
                hold_secs = (trade.exit_time - trade.entry_time).total_seconds()
                trade.hold_minutes = int(hold_secs / 60)

        s.commit()
        log.info(f"Trade closed: {contract_symbol} pnl={trade.realized_pnl}")


def get_open_trade_by_symbol(symbol: str) -> Optional[dict]:
    with _session() as s:
        stmt = (
            select(PaperTrade)
            .where(PaperTrade.contract_symbol == symbol)
            .where(PaperTrade.status == "open")
        )
        trade = s.scalars(stmt).first()
        if not trade:
            return None
        return {
            "id": trade.id,
            "contract_symbol": trade.contract_symbol,
            "trade_type": trade.trade_type,
            "entry_fill_price": trade.entry_fill_price,
            "entry_time": trade.entry_time,
            "expiration": trade.expiration,
            "qty": trade.qty,
        }


def get_today_trades() -> list[dict]:
    today = date.today()
    with _session() as s:
        stmt = select(PaperTrade).where(
            PaperTrade.entry_time >= datetime.combine(today, datetime.min.time())
        )
        return [
            {"symbol": t.contract_symbol, "status": t.status, "pnl": t.realized_pnl}
            for t in s.scalars(stmt).all()
        ]


def count_today_trades() -> int:
    return len([t for t in get_today_trades() if t["status"] in ("open", "closed")])


def record_daily_performance(
    perf_date: date,
    starting_equity: float,
    ending_equity: float,
    realized_pnl: float,
    unrealized_pnl: float,
    spy_close: float,
) -> None:
    today_trades = get_today_trades()
    closed = [t for t in today_trades if t["status"] == "closed"]
    wins = sum(1 for t in closed if (t["pnl"] or 0) > 0)
    losses = sum(1 for t in closed if (t["pnl"] or 0) <= 0)

    with _session() as s:
        row = DailyPerformance(
            date=perf_date,
            starting_equity=starting_equity,
            ending_equity=ending_equity,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            num_trades=len(closed),
            num_wins=wins,
            num_losses=losses,
            spy_close=spy_close,
        )
        s.merge(row)
        s.commit()
