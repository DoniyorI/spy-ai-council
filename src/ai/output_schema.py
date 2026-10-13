from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class AnalystOutput(BaseModel):
    analyst: str
    model: str
    direction: Literal["CALL", "PUT", "NONE"]
    trade_type: Optional[Literal["SCALP", "SHORT_SWING", "SWING"]] = None
    confidence: int = Field(ge=0, le=100)
    preferred_contract_symbol: Optional[str] = None
    reasoning: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    invalidation_level: Optional[float] = None
    expected_hold_time: Optional[Literal["intraday", "1-3 days", "3-7 days"]] = None
    data_quality_score: int = Field(default=50, ge=0, le=100)

    @field_validator("direction", mode="before")
    @classmethod
    def upper_direction(cls, v):
        return str(v).upper() if v else v

    @field_validator("trade_type", mode="before")
    @classmethod
    def upper_trade_type(cls, v):
        if v is None:
            return None
        v = str(v).upper()
        return v if v in ("SCALP", "SHORT_SWING", "SWING") else None


class CommitteeOutput(BaseModel):
    analyst: Literal["risk_committee"]
    model: str
    final_action: Literal["BUY_CALL", "BUY_PUT", "NO_TRADE"]
    trade_type: Optional[Literal["SCALP", "SHORT_SWING", "SWING"]] = None
    confidence: Optional[int] = Field(default=0, ge=0, le=100)
    preferred_contract_symbol: Optional[str] = None
    veto_reason: Optional[str] = None
    agreement_summary: Optional[str] = ""
    rationale_for_type: Optional[str] = ""
    why_this_could_be_wrong: list[str] = Field(default_factory=list)

    @field_validator("final_action", mode="before")
    @classmethod
    def upper_action(cls, v):
        return str(v).upper() if v else v

    @field_validator("trade_type", mode="before")
    @classmethod
    def upper_trade_type(cls, v):
        if v is None:
            return None
        v = str(v).upper()
        return v if v in ("SCALP", "SHORT_SWING", "SWING") else None
