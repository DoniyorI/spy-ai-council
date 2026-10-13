from datetime import datetime, date, timedelta
import pytz

ET = pytz.timezone("America/New_York")
UTC = pytz.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def et_now() -> datetime:
    return datetime.now(ET)


def to_et(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return ET.localize(dt)
    return dt.astimezone(ET)


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return UTC.localize(dt)
    return dt.astimezone(UTC)


def today_et() -> date:
    return et_now().date()


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def dte(expiration: date | str, ref: date | None = None) -> int:
    ref = ref or today_et()
    if isinstance(expiration, str):
        expiration = date.fromisoformat(expiration)
    return (expiration - ref).days
