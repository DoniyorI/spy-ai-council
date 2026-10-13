from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Optional

from config.settings import MIN_CONFIDENCE, CONSERVATIVE_TYPE_ORDER
from src.ai.output_schema import AnalystOutput, CommitteeOutput
from src.utils.logging_config import log


@dataclass
class Decision:
    action: str  # BUY_CALL | BUY_PUT | NO_TRADE
    trade_type: Optional[str] = None
    confidence: float = 0.0
    preferred_symbol: Optional[str] = None
    reason: Optional[str] = None
    vote_breakdown: dict = None

    def __post_init__(self):
        if self.vote_breakdown is None:
            self.vote_breakdown = {}


def _pick_most_conservative(types: list[str]) -> str:
    for t in CONSERVATIVE_TYPE_ORDER:
        if t in types:
            return t
    return types[0]


def _most_common_symbol(outputs: list[AnalystOutput]) -> Optional[str]:
    symbols = [o.preferred_contract_symbol for o in outputs if o.preferred_contract_symbol]
    if not symbols:
        return None
    return Counter(symbols).most_common(1)[0][0]


def tally(p1_p3_outputs: list[AnalystOutput]) -> dict:
    call_votes = sum(1 for o in p1_p3_outputs if o.direction == "CALL")
    put_votes = sum(1 for o in p1_p3_outputs if o.direction == "PUT")
    none_votes = len(p1_p3_outputs) - call_votes - put_votes
    return {"CALL": call_votes, "PUT": put_votes, "NONE": none_votes}


def check_committee_veto(p4_outputs: list[CommitteeOutput]) -> tuple[bool, str]:
    if not p4_outputs:
        return False, ""
    no_trade_count = sum(1 for o in p4_outputs if o.final_action == "NO_TRADE")
    if no_trade_count >= 2:
        reasons = [o.veto_reason for o in p4_outputs if o.veto_reason]
        return True, "; ".join(reasons) if reasons else "risk committee veto (2/3 NO_TRADE)"
    return False, ""


def decide(p1_p3_outputs: list[AnalystOutput], p4_outputs: list[CommitteeOutput]) -> Decision:
    counts = tally(p1_p3_outputs)
    call_v, put_v, none_v = counts["CALL"], counts["PUT"], counts["NONE"]

    log.info(f"Vote tally: CALL={call_v} PUT={put_v} NONE={none_v}")

    total = len(p1_p3_outputs)
    if total == 0:
        return Decision(action="NO_TRADE", reason="no analyst outputs", vote_breakdown=counts)

    # Scale majority threshold by how many votes we actually received.
    # Full council (9): need 5. Partial (3-5): need 2/3 of available votes.
    if total >= 7:
        majority = 5
    elif total >= 4:
        majority = total - 1   # e.g. 4 votes → need 3
    else:
        majority = max(2, total - 1)  # 3 votes → need 2

    log.info(f"Majority threshold: {majority}/{total} votes needed")

    if call_v >= majority:
        winning_dir = "CALL"
        winners = [o for o in p1_p3_outputs if o.direction == "CALL"]
    elif put_v >= majority:
        winning_dir = "PUT"
        winners = [o for o in p1_p3_outputs if o.direction == "PUT"]
    else:
        return Decision(
            action="NO_TRADE",
            reason=f"no majority: CALL={call_v} PUT={put_v} NONE={none_v} (need {majority}/{total})",
            vote_breakdown=counts,
        )

    avg_conf = mean(o.confidence for o in winners)
    if avg_conf < MIN_CONFIDENCE:
        return Decision(
            action="NO_TRADE",
            reason=f"avg confidence {avg_conf:.1f} < {MIN_CONFIDENCE}",
            vote_breakdown=counts,
        )

    type_votes = Counter(o.trade_type for o in winners if o.trade_type)
    if not type_votes:
        return Decision(
            action="NO_TRADE",
            reason="winners did not propose a trade type",
            vote_breakdown=counts,
        )

    winner_type, type_count = type_votes.most_common(1)[0]
    if type_count < len(winners) / 2:
        winner_type = _pick_most_conservative(list(type_votes.keys()))
        log.info(f"Type split — falling back to conservative type: {winner_type}")

    # Committee veto check
    vetoed, veto_reason = check_committee_veto(p4_outputs)
    if vetoed:
        return Decision(
            action="NO_TRADE",
            reason=veto_reason,
            vote_breakdown={**counts, "types": dict(type_votes)},
        )

    # Committee may override trade_type
    p4_types = Counter(o.trade_type for o in p4_outputs if o.trade_type)
    if p4_types:
        p4_top_type, p4_top_count = p4_types.most_common(1)[0]
        if p4_top_count >= 2 and p4_top_type != winner_type:
            log.info(f"Committee overrides trade_type: {winner_type} → {p4_top_type}")
            winner_type = p4_top_type

    preferred_symbol = _most_common_symbol(winners)

    return Decision(
        action=f"BUY_{winning_dir}",
        trade_type=winner_type,
        confidence=round(avg_conf, 1),
        preferred_symbol=preferred_symbol,
        vote_breakdown={
            "directions": counts,
            "types": dict(type_votes),
            "p4_types": dict(p4_types),
        },
    )
