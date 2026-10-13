"""Smoke test: each AI model returns valid JSON from all 4 prompts."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from src.ai.prompt_runner import run_council, load_prompts
from src.ai.output_schema import AnalystOutput, CommitteeOutput

console = Console()

# Minimal synthetic context for testing
MOCK_CONTEXT = {
    "as_of": "2026-04-25T13:00:00Z",
    "ticker": "SPY",
    "account": {"equity": 1000, "cash": 1000, "buying_power": 1000, "trades_today": 0, "max_trade_size_usd": 100, "max_trades_today": 2},
    "spot": {"last": 510.0, "bid": 509.9, "ask": 510.1, "prior_close": 508.0, "daily_change_pct": 0.39, "premarket_gap_pct": 0.1},
    "volume": {"today": 40000000, "avg_20d": 62000000, "ratio": 0.65},
    "indicators": {
        "sma_10": 508.5, "sma_50": 502.0, "sma_200": 490.0,
        "rsi_14": 57.0, "macd": 1.2, "macd_signal": 1.0, "macd_histogram": 0.2,
        "atr_14": 4.5, "vwap_today": 509.5, "bb_upper": 515.0, "bb_lower": 503.0,
    },
    "trend_summary": {"short_term": "bullish", "medium_term": "bullish", "long_term": "bullish", "alignment": "10>50>200"},
    "options_universe": {
        "SCALP": {
            "calls": [{"symbol": "SPY260425C00512000", "strike": 512, "expiration": "2026-04-30", "dte": 5, "type": "call", "bid": 1.5, "ask": 1.7, "mid": 1.6, "spread_pct": 12.5, "volume": 800, "open_interest": 3000, "implied_volatility": 0.18, "delta": 0.45, "gamma": 0.05, "theta": -0.08, "vega": 0.12}],
            "puts": [{"symbol": "SPY260425P00508000", "strike": 508, "expiration": "2026-04-30", "dte": 5, "type": "put", "bid": 1.3, "ask": 1.5, "mid": 1.4, "spread_pct": 14.3, "volume": 600, "open_interest": 2500, "implied_volatility": 0.19, "delta": -0.40, "gamma": 0.04, "theta": -0.07, "vega": 0.11}],
        },
        "SHORT_SWING": {
            "calls": [{"symbol": "SPY260515C00515000", "strike": 515, "expiration": "2026-05-15", "dte": 20, "type": "call", "bid": 3.0, "ask": 3.3, "mid": 3.15, "spread_pct": 9.5, "volume": 300, "open_interest": 1200, "implied_volatility": 0.17, "delta": 0.42, "gamma": 0.03, "theta": -0.04, "vega": 0.18}],
            "puts": [{"symbol": "SPY260515P00505000", "strike": 505, "expiration": "2026-05-15", "dte": 20, "type": "put", "bid": 2.8, "ask": 3.0, "mid": 2.9, "spread_pct": 6.9, "volume": 250, "open_interest": 1100, "implied_volatility": 0.18, "delta": -0.38, "gamma": 0.03, "theta": -0.03, "vega": 0.17}],
        },
        "SWING": {
            "calls": [{"symbol": "SPY260620C00520000", "strike": 520, "expiration": "2026-06-20", "dte": 56, "type": "call", "bid": 5.0, "ask": 5.4, "mid": 5.2, "spread_pct": 7.7, "volume": 80, "open_interest": 600, "implied_volatility": 0.16, "delta": 0.38, "gamma": 0.02, "theta": -0.02, "vega": 0.22}],
            "puts": [{"symbol": "SPY260620P00500000", "strike": 500, "expiration": "2026-06-20", "dte": 56, "type": "put", "bid": 4.5, "ask": 4.9, "mid": 4.7, "spread_pct": 8.5, "volume": 60, "open_interest": 550, "implied_volatility": 0.17, "delta": -0.35, "gamma": 0.02, "theta": -0.02, "vega": 0.21}],
        },
    },
    "news_last_24h": [{"headline": "Fed holds rates steady", "summary": "FOMC meeting left rates unchanged as expected.", "source": "Reuters", "published_at": "2026-04-25T10:00:00Z", "url": ""}],
    "vix": 14.5,
    "is_fomc_week": False,
    "is_cpi_week": False,
    "is_earnings_week_for_megacaps": False,
}


async def run():
    console.rule("[bold green]AI Council Smoke Test")

    results = await run_council(MOCK_CONTEXT)

    t = Table(title="Analyst Outputs (P1–P3)")
    t.add_column("Model")
    t.add_column("Prompt")
    t.add_column("Direction")
    t.add_column("Type")
    t.add_column("Conf")
    t.add_column("Symbol")
    t.add_column("Latency")
    t.add_column("Valid?")

    for r in results.raw_results:
        if r.prompt_name == "risk_committee":
            continue
        valid = "[green]✓" if r.parsed else "[red]✗"
        parsed = r.parsed
        t.add_row(
            r.model_name,
            r.prompt_name,
            getattr(parsed, "direction", "?") if parsed else "FAIL",
            getattr(parsed, "trade_type", "?") if parsed else "-",
            str(getattr(parsed, "confidence", "?")) if parsed else "-",
            (getattr(parsed, "preferred_contract_symbol", "") or "")[:25] if parsed else "-",
            f"{r.latency_ms}ms",
            valid,
        )
    console.print(t)

    t2 = Table(title="Committee Outputs (P4)")
    t2.add_column("Model")
    t2.add_column("Action")
    t2.add_column("Type")
    t2.add_column("Conf")
    t2.add_column("Veto")
    t2.add_column("Valid?")

    for r in results.raw_results:
        if r.prompt_name != "risk_committee":
            continue
        valid = "[green]✓" if r.parsed else "[red]✗"
        parsed = r.parsed
        t2.add_row(
            r.model_name,
            getattr(parsed, "final_action", "FAIL") if parsed else "FAIL",
            str(getattr(parsed, "trade_type", "?")) if parsed else "-",
            str(getattr(parsed, "confidence", "?")) if parsed else "-",
            str(getattr(parsed, "veto_reason", "")) if parsed else "-",
            valid,
        )
    console.print(t2)

    valid_count = sum(1 for r in results.raw_results if r.parsed)
    total_count = len(results.raw_results)
    console.print(f"\n[bold]Valid outputs: {valid_count}/{total_count}[/bold]")

    if valid_count < total_count:
        console.print("[yellow]Some outputs failed to parse — check API keys and model names")
    else:
        console.print("[green]All outputs valid!")


if __name__ == "__main__":
    asyncio.run(run())
