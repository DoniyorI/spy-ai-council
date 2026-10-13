from datetime import datetime, timedelta

from alpaca.data.requests import NewsRequest

from src.brokers.alpaca_client import get_news_client
from src.utils.time_helpers import utc_now
from src.utils.logging_config import log


def get_recent_news(symbol: str = "SPY", hours: int = 24, limit: int = 20) -> list[dict]:
    client = get_news_client()
    start = utc_now() - timedelta(hours=hours)
    try:
        resp = client.get_news(
            NewsRequest(
                symbols=symbol,
                start=start,
                limit=limit,
                sort="desc",
            )
        )
        articles = resp.news if hasattr(resp, "news") else []
        return [
            {
                "headline": a.headline,
                "summary": a.summary or "",
                "source": a.source or "",
                "published_at": str(a.created_at),
                "url": a.url or "",
            }
            for a in articles
        ]
    except Exception as e:
        log.warning(f"News fetch error: {e}")
        return []
