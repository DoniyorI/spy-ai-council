from datetime import datetime, time, date, timedelta

import pytz

ET = pytz.timezone("America/New_York")

# US market holidays 2026 (add more years as needed)
_HOLIDAYS_2026: set[date] = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas
}

_HOLIDAYS_2025: set[date] = {
    date(2025, 1, 1),
    date(2025, 1, 20),
    date(2025, 2, 17),
    date(2025, 4, 18),
    date(2025, 5, 26),
    date(2025, 6, 19),
    date(2025, 7, 4),
    date(2025, 9, 1),
    date(2025, 11, 27),
    date(2025, 12, 25),
}

_ALL_HOLIDAYS = _HOLIDAYS_2025 | _HOLIDAYS_2026

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def now_et() -> datetime:
    return datetime.now(ET)


def is_trading_day(dt: datetime | date | None = None) -> bool:
    d = (dt if isinstance(dt, date) else (dt.date() if dt else now_et().date()))
    if hasattr(d, "weekday"):
        if d.weekday() >= 5:
            return False
    if d in _ALL_HOLIDAYS:
        return False
    return True


def is_market_open(dt: datetime | None = None, buffer_min: int = 0) -> bool:
    dt = dt or now_et()
    if not is_trading_day(dt):
        return False
    t = dt.astimezone(ET).time()
    open_buf = (
        datetime.combine(date.today(), MARKET_OPEN, tzinfo=ET)
        + timedelta(minutes=buffer_min)
    ).time()
    close_buf = (
        datetime.combine(date.today(), MARKET_CLOSE, tzinfo=ET)
        - timedelta(minutes=buffer_min)
    ).time()
    return open_buf <= t < close_buf


def minutes_to_close(dt: datetime | None = None) -> float:
    dt = dt or now_et()
    dt_et = dt.astimezone(ET)
    close_dt = ET.localize(
        datetime.combine(dt_et.date(), MARKET_CLOSE)
    )
    return (close_dt - dt_et).total_seconds() / 60


def is_within_n_min_of_close(n: int, dt: datetime | None = None) -> bool:
    return 0 <= minutes_to_close(dt) <= n


def next_market_open(dt: datetime | None = None) -> datetime:
    dt = (dt or now_et()).astimezone(ET)
    candidate = dt.date()
    for _ in range(14):
        candidate += timedelta(days=1)
        if is_trading_day(candidate):
            return ET.localize(datetime.combine(candidate, MARKET_OPEN))
    raise RuntimeError("Could not find next market open")


def next_market_close(dt: datetime | None = None) -> datetime:
    dt = (dt or now_et()).astimezone(ET)
    d = dt.date()
    if is_trading_day(d) and dt.time() < MARKET_CLOSE:
        return ET.localize(datetime.combine(d, MARKET_CLOSE))
    return next_market_open(dt).replace(hour=16, minute=0, second=0, microsecond=0)


def trading_days_between(start: datetime, end: datetime) -> int:
    count = 0
    cur = start.date() + timedelta(days=1)
    while cur <= end.date():
        if is_trading_day(cur):
            count += 1
        cur += timedelta(days=1)
    return count
