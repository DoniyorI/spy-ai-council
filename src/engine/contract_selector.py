from typing import Optional

import pandas as pd

from config.settings import TRADE_TYPE_CONFIG
from src.utils.logging_config import log


def select(
    direction: str,
    chain: pd.DataFrame,
    trade_type: str,
    ai_preferred: Optional[str] = None,
) -> Optional[dict]:
    if chain.empty:
        log.warning("Empty options chain — cannot select contract")
        return None

    cfg = TRADE_TYPE_CONFIG.get(trade_type)
    if cfg is None:
        log.error(f"Unknown trade_type: {trade_type}")
        return None

    opt_type = "call" if "CALL" in direction.upper() else "put"

    candidates = chain[
        (chain["type"] == opt_type)
        & (chain["dte"] >= cfg["dte_min"])
        & (chain["dte"] <= cfg["dte_max"])
        & (chain["spread_pct"] <= cfg["max_spread_pct"])
        & (chain["open_interest"] >= cfg["min_open_interest"])
        & (chain["volume"] >= cfg["min_volume"])
        & (chain["mid"] * 100 <= cfg["max_position_size_usd"])
        & (chain["bid"] > 0)
        & (chain["mid"] >= 0.20)
    ].copy()

    # Delta filter (use abs for puts)
    if "delta" in candidates.columns:
        candidates = candidates[
            candidates["delta"].apply(
                lambda d: cfg["delta_min"] <= abs(d) <= cfg["delta_max"]
                if pd.notna(d)
                else True
            )
        ]

    if candidates.empty:
        log.warning(f"No candidates after filters for {direction}/{trade_type}")
        return None

    # Prefer AI's suggestion if it's in the filtered set
    if ai_preferred:
        match = candidates[candidates["symbol"] == ai_preferred]
        if not match.empty:
            log.info(f"Using AI-preferred contract: {ai_preferred}")
            return match.iloc[0].to_dict()

    # Deterministic pick: closest to target delta, tie-break on spread
    target_delta = (cfg["delta_min"] + cfg["delta_max"]) / 2
    if "delta" in candidates.columns:
        candidates["_delta_score"] = (candidates["delta"].abs() - target_delta).abs()
        selected = candidates.sort_values(["_delta_score", "spread_pct"]).iloc[0]
    else:
        selected = candidates.sort_values("spread_pct").iloc[0]

    log.info(
        f"Selected contract: {selected['symbol']} "
        f"delta={selected.get('delta'):.3f} "
        f"mid={selected['mid']:.2f} "
        f"dte={selected['dte']}"
    )
    return selected.to_dict()
