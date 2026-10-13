from datetime import date

from tabulate import tabulate

from src.db import repository as repo
from src.brokers.alpaca_client import get_account
from src.data.market_data import get_spy_bars
from src.utils.logging_config import log


def generate_report(report_date: date) -> str:
    account = get_account()
    trades = repo.get_today_trades()
    closed = [t for t in trades if t["status"] == "closed"]

    spy_bars = get_spy_bars("1Day", 2)
    spy_close = float(spy_bars.iloc[-1]["close"]) if not spy_bars.empty else None

    total_pnl = sum(t["pnl"] or 0 for t in closed)
    wins = sum(1 for t in closed if (t["pnl"] or 0) > 0)
    losses = len(closed) - wins
    win_rate = wins / len(closed) * 100 if closed else 0

    lines = [
        "",
        "=" * 55,
        f"  SPY AI TRADER — Daily Report {report_date}",
        "=" * 55,
        f"  Equity:         ${account['equity']:.2f}",
        f"  Realized PnL:   ${total_pnl:.2f}",
        f"  Trades:         {len(closed)} (W:{wins} L:{losses} WR:{win_rate:.0f}%)",
        f"  SPY Close:      {spy_close or 'N/A'}",
        "",
    ]

    if closed:
        table_data = []
        for t in closed:
            table_data.append([t["symbol"], f"${t['pnl']:.2f}" if t["pnl"] else "-"])
        lines.append(tabulate(table_data, headers=["Contract", "PnL"], tablefmt="simple"))
        lines.append("")

    lines.append("=" * 55)

    report = "\n".join(lines)

    # Save to DB
    try:
        starting_equity = account["equity"] - total_pnl
        repo.record_daily_performance(
            perf_date=report_date,
            starting_equity=starting_equity,
            ending_equity=account["equity"],
            realized_pnl=total_pnl,
            unrealized_pnl=0.0,
            spy_close=spy_close or 0.0,
        )
    except Exception as e:
        log.warning(f"Failed to save daily perf: {e}")

    return report
