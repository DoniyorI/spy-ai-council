"""Smoke test: Alpaca connectivity, account state, options chain, order round-trip."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from src.brokers.alpaca_client import (
    get_trading_client, get_stock_data_client, get_option_data_client,
    get_account, get_positions, get_open_orders, get_clock,
    submit_option_order, cancel_order,
)
from src.data.market_data import get_spy_quote, get_spy_bars
from src.data.options_data import fetch_chain, filter_liquid

console = Console()


def run():
    console.rule("[bold green]Alpaca Smoke Test")

    # 1. Clock
    clock = get_clock()
    console.print(f"Market open: [bold]{clock['is_open']}[/bold]  next_open={clock['next_open']}")

    # 2. Account
    acct = get_account()
    t = Table(title="Account")
    t.add_column("Field")
    t.add_column("Value")
    for k, v in acct.items():
        t.add_row(k, str(v))
    console.print(t)

    if acct["options_trading_level"] < 2:
        console.print("[red]WARNING: Options trading level < 2 — options orders will be rejected!")

    # 3. SPY quote
    q = get_spy_quote()
    console.print(f"SPY quote: bid={q['bid']} ask={q['ask']} mid={q['mid']}")

    # 4. Options chain
    console.print("Fetching SPY options chain (14–30 DTE)...")
    chain = fetch_chain(min_dte=14, max_dte=30)
    if chain.empty:
        console.print("[red]Options chain empty — check API permissions or market hours")
    else:
        liquid = filter_liquid(chain)
        calls = liquid[liquid["type"] == "call"].head(5)
        puts = liquid[liquid["type"] == "put"].head(5)

        COLS = ["symbol", "strike", "dte", "bid", "ask", "delta", "spread_pct"]

        ct = Table(title="Top 5 Calls (liquid)")
        for col in COLS:
            ct.add_column(col)
        for _, row in calls.iterrows():
            ct.add_row(*[str(row.get(c, "")) for c in COLS])
        console.print(ct)

        pt = Table(title="Top 5 Puts (liquid)")
        for col in COLS:
            pt.add_column(col)
        for _, row in puts.iterrows():
            pt.add_row(*[str(row.get(c, "")) for c in COLS])
        console.print(pt)

    # 5. Order round-trip (stock) — tiny limit far from market, cancel immediately
    console.print("Placing + cancelling test stock order...")
    try:
        from alpaca.trading.requests import LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        spy_price = q["bid"] * 0.5 if q["bid"] else 400.0
        order = get_trading_client().submit_order(
            LimitOrderRequest(
                symbol="SPY", qty=1, side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                limit_price=round(spy_price, 2),
            )
        )
        cancel_order(str(order.id))
        console.print(f"[green]Stock order test: OK (order {order.id} placed + cancelled)")
    except Exception as e:
        console.print(f"[red]Stock order test failed: {e}")

    # 6. Options order (far OTM, won't fill)
    calls = chain[chain["type"] == "call"] if not chain.empty else pd.DataFrame()
    if not calls.empty:
        console.print("Placing + cancelling test options order (far OTM)...")
        try:
            otm = calls.sort_values("strike", ascending=False).iloc[0]
            order = submit_option_order(otm["symbol"], 1, "BUY", 0.01)
            cancel_order(order["id"])
            console.print(f"[green]Options order test: OK ({otm['symbol']} placed + cancelled)")
        except Exception as e:
            console.print(f"[red]Options order test failed: {e}")

    console.rule("[bold green]All checks done")


if __name__ == "__main__":
    run()
