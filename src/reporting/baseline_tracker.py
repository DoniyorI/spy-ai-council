"""
Track two baselines against the bot's PnL:
1. SPY buy-and-hold (invest $1000 in SPY shares on day 1)
2. Random trade baseline (flip a coin each day, same sizing)
"""
import random
from datetime import date

from src.db.models import DailyPerformance
from src.db.repository import _session
from sqlalchemy import select


def spy_buyhold_pct(start_date: date, end_date: date, starting_equity: float = 1000.0) -> float:
    """Return % gain of SPY buy-hold from start to end using stored spy_close values."""
    with _session() as s:
        rows = s.scalars(
            select(DailyPerformance)
            .where(DailyPerformance.date >= start_date)
            .where(DailyPerformance.date <= end_date)
            .order_by(DailyPerformance.date)
        ).all()

    if len(rows) < 2:
        return 0.0

    start_spy = rows[0].spy_close
    end_spy = rows[-1].spy_close
    if not start_spy:
        return 0.0
    return round((end_spy - start_spy) / start_spy * 100, 2)


def random_baseline_pct(num_days: int, daily_risk_pct: float = 3.0, seed: int = 42) -> float:
    """Simulate random directional bets (50/50) with same daily risk per trade."""
    rng = random.Random(seed)
    equity = 100.0
    for _ in range(num_days):
        direction = rng.choice([1, -1])
        equity *= (1 + direction * daily_risk_pct / 100)
    return round(equity - 100, 2)
