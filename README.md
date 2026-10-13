# SPY AI Trader

Paper-trading bot with an AI council (Claude + GPT + Gemini) making 1–2 SPY options trades per day.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
```

## Smoke tests

```bash
python scripts/verify_alpaca.py   # account + chain + order round-trip
python scripts/verify_ai.py       # all 12 AI calls return valid JSON
```

## Full pipeline dry run

```bash
python scripts/run_once.py --dry-run
```

## Run tests

```bash
pytest
```

## Cron (macOS/Linux, America/New_York)

```cron
35  9  * * 1-5  cd /path/to/spy-ai-trader && .venv/bin/python -m src.jobs.morning_scan
*/5 9-15 * * 1-5  cd /path/to/spy-ai-trader && .venv/bin/python -m src.jobs.position_monitor
30  11 * * 1-5  cd /path/to/spy-ai-trader && .venv/bin/python -m src.jobs.midday_scan
30  13 * * 1-5  cd /path/to/spy-ai-trader && .venv/bin/python -m src.jobs.midday_scan
30  15 * * 1-5  cd /path/to/spy-ai-trader && .venv/bin/python -m src.jobs.position_monitor --force-scalp-close
55  15 * * 1-5  cd /path/to/spy-ai-trader && .venv/bin/python -m src.jobs.position_monitor --force-scalp-close
15  16 * * 1-5  cd /path/to/spy-ai-trader && .venv/bin/python -m src.jobs.eod_report
```

## Kill switch

```bash
touch KILL_SWITCH   # all jobs check for this and exit immediately
rm KILL_SWITCH      # re-enable
```
