import time as _time
from functools import lru_cache

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetOrdersRequest,
    MarketOrderRequest,
    LimitOrderRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    StockBarsRequest,
    OptionLatestQuoteRequest,
    OptionChainRequest,
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest

from config.settings import ALPACA_API_KEY, ALPACA_SECRET_KEY
from src.utils.logging_config import log


@lru_cache(maxsize=1)
def get_trading_client() -> TradingClient:
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)


@lru_cache(maxsize=1)
def get_stock_data_client() -> StockHistoricalDataClient:
    return StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)


@lru_cache(maxsize=1)
def get_option_data_client() -> OptionHistoricalDataClient:
    return OptionHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)


@lru_cache(maxsize=1)
def get_news_client() -> NewsClient:
    return NewsClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)


def get_account() -> dict:
    acct = get_trading_client().get_account()
    return {
        "equity": float(acct.equity),
        "cash": float(acct.cash),
        "buying_power": float(acct.buying_power),
        "options_buying_power": float(getattr(acct, "options_buying_power", acct.buying_power)),
        "options_trading_level": int(getattr(acct, "options_approved_level", 0)),
    }


def get_positions() -> list[dict]:
    positions = get_trading_client().get_all_positions()
    result = []
    for p in positions:
        result.append({
            "symbol": p.symbol,
            "qty": float(p.qty),
            "avg_entry_price": float(p.avg_entry_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc),
            "asset_class": str(p.asset_class),
            "is_option": str(p.asset_class) == "us_option",
        })
    return result


def get_open_orders() -> list[dict]:
    req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
    orders = get_trading_client().get_orders(req)
    return [
        {
            "id": str(o.id),
            "symbol": o.symbol,
            "qty": float(o.qty or 0),
            "side": str(o.side),
            "status": str(o.status),
            "limit_price": float(o.limit_price) if o.limit_price else None,
            "filled_avg_price": float(o.filled_avg_price) if o.filled_avg_price else None,
        }
        for o in orders
    ]


def submit_option_order(symbol: str, qty: int, side: str, limit_price: float) -> dict:
    from alpaca.trading.requests import LimitOrderRequest
    from alpaca.trading.enums import OrderType

    req = LimitOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
        type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        limit_price=round(limit_price, 2),
    )
    order = get_trading_client().submit_order(req)
    return {
        "id": str(order.id),
        "symbol": order.symbol,
        "status": str(order.status),
        "limit_price": float(order.limit_price) if order.limit_price else None,
    }


def cancel_order(order_id: str) -> None:
    get_trading_client().cancel_order_by_id(order_id)


def wait_for_fill(order_id: str, timeout: int = 60) -> dict | None:
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        order = get_trading_client().get_order_by_id(order_id)
        status = str(order.status)
        if status == "filled":
            return {
                "id": str(order.id),
                "symbol": order.symbol,
                "filled_avg_price": float(order.filled_avg_price),
                "filled_qty": float(order.filled_qty),
                "status": status,
            }
        if status in ("cancelled", "expired", "rejected"):
            log.warning(f"Order {order_id} terminal status: {status}")
            return None
        _time.sleep(3)
    log.warning(f"Order {order_id} not filled after {timeout}s — cancelling")
    try:
        cancel_order(order_id)
    except Exception:
        pass
    return None


def get_clock() -> dict:
    clock = get_trading_client().get_clock()
    return {
        "is_open": clock.is_open,
        "next_open": str(clock.next_open),
        "next_close": str(clock.next_close),
    }
