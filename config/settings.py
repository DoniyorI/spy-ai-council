import os
from dotenv import load_dotenv

load_dotenv()

# --- Alpaca ---
ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_DATA_URL = os.getenv("ALPACA_DATA_URL", "https://data.alpaca.markets")

# --- AI Models ---
CLAUDE_ANALYST_MODEL = os.getenv("CLAUDE_ANALYST_MODEL", "claude-sonnet-4-6")
OPENAI_ANALYST_MODEL = os.getenv("OPENAI_ANALYST_MODEL", "gpt-4o")
GEMINI_ANALYST_MODEL = os.getenv("GEMINI_ANALYST_MODEL", "gemini-1.5-pro")

CLAUDE_COMMITTEE_MODEL = os.getenv("CLAUDE_COMMITTEE_MODEL", "claude-opus-4-7")
OPENAI_COMMITTEE_MODEL = os.getenv("OPENAI_COMMITTEE_MODEL", "gpt-4o")
GEMINI_COMMITTEE_MODEL = os.getenv("GEMINI_COMMITTEE_MODEL", "gemini-1.5-pro")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

# --- DB ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/trader.db")

# --- Mode ---
TRADING_MODE = os.getenv("TRADING_MODE", "paper")  # paper | dry_run
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# --- Account-level limits ---
MAX_TRADES_PER_DAY = 2
MIN_EQUITY_FLOOR = 700           # halt trading if equity drops below this
DAILY_LOSS_LIMIT_PCT = 5.0       # halt if today's realized PnL% <= -5%
MIN_CONFIDENCE = 70              # minimum avg confidence to proceed to trade

# --- Trade-type config ---
TRADE_TYPE_CONFIG: dict[str, dict] = {
    "SCALP": {
        "dte_min": 1, "dte_max": 7,
        "delta_min": 0.40, "delta_max": 0.60,
        "max_spread_pct": 8,
        "min_open_interest": 2000,
        "min_volume": 500,
        "max_position_size_usd": 50,
        "take_profit_pct": 25,
        "stop_loss_pct": 20,
        "max_hold_days": 1,
        "dte_force_exit": 1,
    },
    "SHORT_SWING": {
        "dte_min": 7, "dte_max": 21,
        "delta_min": 0.35, "delta_max": 0.55,
        "max_spread_pct": 12,
        "min_open_interest": 1000,
        "min_volume": 200,
        "max_position_size_usd": 100,
        "take_profit_pct": 40,
        "stop_loss_pct": 30,
        "max_hold_days": 3,
        "dte_force_exit": 5,
    },
    "SWING": {
        "dte_min": 21, "dte_max": 45,
        "delta_min": 0.30, "delta_max": 0.50,
        "max_spread_pct": 15,
        "min_open_interest": 500,
        "min_volume": 50,
        "max_position_size_usd": 100,
        "take_profit_pct": 60,
        "stop_loss_pct": 40,
        "max_hold_days": 7,
        "dte_force_exit": 10,
    },
}

CONSERVATIVE_TYPE_ORDER = ["SWING", "SHORT_SWING", "SCALP"]
