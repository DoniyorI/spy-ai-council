"""Cancel all open orders and close all positions on the paper account."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.brokers.alpaca_client import get_trading_client, get_positions, get_open_orders, cancel_order
from src.utils.logging_config import log
from rich.console import Console

console = Console()


def main():
    console.print("[bold red]Resetting paper account — cancelling all orders + closing all positions")
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        console.print("Aborted.")
        return

    client = get_trading_client()

    orders = get_open_orders()
    for o in orders:
        try:
            cancel_order(o["id"])
            console.print(f"Cancelled order: {o['id']} {o['symbol']}")
        except Exception as e:
            console.print(f"[red]Error cancelling {o['id']}: {e}")

    positions = get_positions()
    for p in positions:
        try:
            client.close_position(p["symbol"])
            console.print(f"Closed position: {p['symbol']}")
        except Exception as e:
            console.print(f"[red]Error closing {p['symbol']}: {e}")

    console.print("[green]Done. Paper account reset.")


if __name__ == "__main__":
    main()
