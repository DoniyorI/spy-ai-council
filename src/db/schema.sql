CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_time TIMESTAMP NOT NULL,
    scan_type TEXT NOT NULL,
    context_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER REFERENCES scans(id),
    model TEXT NOT NULL,
    prompt_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL DEFAULT 'v1',
    raw_output TEXT NOT NULL,
    parsed_json TEXT NOT NULL,
    direction TEXT,
    confidence REAL,
    preferred_symbol TEXT,
    latency_ms INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER REFERENCES scans(id),
    final_action TEXT NOT NULL,
    trade_type TEXT,
    confidence REAL,
    vote_breakdown_json TEXT,
    risk_gate_result TEXT,
    risk_block_reason TEXT,
    selected_contract TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER REFERENCES decisions(id),
    alpaca_order_id TEXT UNIQUE,
    contract_symbol TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    side TEXT NOT NULL,
    qty INTEGER NOT NULL,
    entry_limit_price REAL,
    entry_fill_price REAL,
    entry_time TIMESTAMP,
    expiration TEXT,
    exit_fill_price REAL,
    exit_time TIMESTAMP,
    exit_reason TEXT,
    realized_pnl REAL,
    realized_pnl_pct REAL,
    hold_minutes INTEGER,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS daily_performance (
    date DATE PRIMARY KEY,
    starting_equity REAL,
    ending_equity REAL,
    realized_pnl REAL,
    unrealized_pnl REAL,
    num_trades INTEGER,
    num_wins INTEGER,
    num_losses INTEGER,
    spy_close REAL,
    baseline_random_pnl REAL,
    baseline_buyhold_pnl REAL
);

CREATE INDEX IF NOT EXISTS idx_ai_outputs_scan ON ai_outputs(scan_id);
CREATE INDEX IF NOT EXISTS idx_decisions_scan ON decisions(scan_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON paper_trades(contract_symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON paper_trades(status);
