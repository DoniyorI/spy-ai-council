from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, Date,
    ForeignKey, Boolean, create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Scan(Base):
    __tablename__ = "scans"
    id = Column(Integer, primary_key=True)
    scan_time = Column(DateTime, nullable=False)
    scan_type = Column(String, nullable=False)
    context_json = Column(Text, nullable=False)
    ai_outputs = relationship("AIOutput", back_populates="scan")
    decisions = relationship("Decision", back_populates="scan")


class AIOutput(Base):
    __tablename__ = "ai_outputs"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    model = Column(String, nullable=False)
    prompt_name = Column(String, nullable=False)
    prompt_version = Column(String, default="v1")
    raw_output = Column(Text, nullable=False)
    parsed_json = Column(Text, nullable=False)
    direction = Column(String)
    confidence = Column(Float)
    preferred_symbol = Column(String)
    latency_ms = Column(Integer)
    cost_usd = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    scan = relationship("Scan", back_populates="ai_outputs")


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    final_action = Column(String, nullable=False)
    trade_type = Column(String)
    confidence = Column(Float)
    vote_breakdown_json = Column(Text)
    risk_gate_result = Column(String)
    risk_block_reason = Column(String)
    selected_contract = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    scan = relationship("Scan", back_populates="decisions")
    trades = relationship("PaperTrade", back_populates="decision")


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id = Column(Integer, primary_key=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"))
    alpaca_order_id = Column(String, unique=True)
    contract_symbol = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)
    side = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    entry_limit_price = Column(Float)
    entry_fill_price = Column(Float)
    entry_time = Column(DateTime)
    expiration = Column(String)
    exit_fill_price = Column(Float)
    exit_time = Column(DateTime)
    exit_reason = Column(String)
    realized_pnl = Column(Float)
    realized_pnl_pct = Column(Float)
    hold_minutes = Column(Integer)
    status = Column(String, default="pending")
    decision = relationship("Decision", back_populates="trades")


class DailyPerformance(Base):
    __tablename__ = "daily_performance"
    date = Column(Date, primary_key=True)
    starting_equity = Column(Float)
    ending_equity = Column(Float)
    realized_pnl = Column(Float)
    unrealized_pnl = Column(Float)
    num_trades = Column(Integer)
    num_wins = Column(Integer)
    num_losses = Column(Integer)
    spy_close = Column(Float)
    baseline_random_pnl = Column(Float)
    baseline_buyhold_pnl = Column(Float)
