import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import (
    CLAUDE_ANALYST_MODEL,
    OPENAI_ANALYST_MODEL,
    GEMINI_ANALYST_MODEL,
    CLAUDE_COMMITTEE_MODEL,
    OPENAI_COMMITTEE_MODEL,
    GEMINI_COMMITTEE_MODEL,
)
from src.ai.base import CouncilMember
from src.ai.claude_member import ClaudeMember
from src.ai.openai_member import OpenAIMember
from src.ai.gemini_member import GeminiMember
from src.ai.output_schema import AnalystOutput, CommitteeOutput
from src.ai.parser import parse_strict
from src.utils.logging_config import log

PROMPT_DIR = Path("config/prompts")
ANALYST_PROMPTS = ["trend_momentum", "reversal_fade", "macro_catalyst"]
COMMITTEE_PROMPT = "risk_committee"


@dataclass
class RawResult:
    model_name: str
    prompt_name: str
    raw_text: str
    latency_ms: int
    parsed: AnalystOutput | CommitteeOutput | None


@dataclass
class CouncilResults:
    p1_p3_outputs: list[AnalystOutput] = field(default_factory=list)
    p4_outputs: list[CommitteeOutput] = field(default_factory=list)
    raw_results: list[RawResult] = field(default_factory=list)


def load_prompts() -> dict[str, str]:
    prompts = {}
    for f in PROMPT_DIR.glob("*.md"):
        prompts[f.stem] = f.read_text()
    return prompts


def _make_user_message(context: dict) -> str:
    return f"Current market context:\n\n{json.dumps(context, indent=2, default=str)}"


def _make_committee_message(context: dict, analyst_outputs: list[AnalystOutput]) -> str:
    analyst_data = [o.model_dump() for o in analyst_outputs]
    return (
        f"Analyst council outputs (9 votes):\n\n"
        f"{json.dumps(analyst_data, indent=2)}\n\n"
        f"Full market context:\n\n{json.dumps(context, indent=2, default=str)}"
    )


async def _run_one(
    member: CouncilMember,
    model: str,
    system_prompt: str,
    user_message: str,
    prompt_name: str,
    schema,
) -> RawResult:
    t0 = time.monotonic()
    raw = await member.call(system_prompt, user_message, model)
    latency_ms = int((time.monotonic() - t0) * 1000)
    parsed = parse_strict(raw, schema)
    if parsed is None:
        log.warning(f"[{member.name}/{model}/{prompt_name}] parse failed")
    return RawResult(
        model_name=f"{member.name}/{model}",
        prompt_name=prompt_name,
        raw_text=raw,
        latency_ms=latency_ms,
        parsed=parsed,
    )


async def run_council(context: dict) -> CouncilResults:
    prompts = load_prompts()
    members: list[tuple[CouncilMember, str]] = [
        (ClaudeMember(), CLAUDE_ANALYST_MODEL),
        (OpenAIMember(), OPENAI_ANALYST_MODEL),
        (GeminiMember(), GEMINI_ANALYST_MODEL),
    ]
    user_msg = _make_user_message(context)
    results = CouncilResults()

    # P1–P3: 9 calls in parallel
    analyst_tasks = []
    for prompt_name in ANALYST_PROMPTS:
        system_prompt = prompts.get(prompt_name, "")
        for member, model in members:
            analyst_tasks.append(
                _run_one(member, model, system_prompt, user_msg, prompt_name, AnalystOutput)
            )

    log.info(f"Running {len(analyst_tasks)} analyst calls in parallel...")
    analyst_raw = await asyncio.gather(*analyst_tasks)
    results.raw_results.extend(analyst_raw)

    for r in analyst_raw:
        if r.parsed and isinstance(r.parsed, AnalystOutput):
            results.p1_p3_outputs.append(r.parsed)

    log.info(f"Analyst phase done: {len(results.p1_p3_outputs)}/9 valid outputs")

    # P4: 3 committee calls sequentially on same data (no need to parallelize across members)
    committee_members: list[tuple[CouncilMember, str]] = [
        (ClaudeMember(), CLAUDE_COMMITTEE_MODEL),
        (OpenAIMember(), OPENAI_COMMITTEE_MODEL),
        (GeminiMember(), GEMINI_COMMITTEE_MODEL),
    ]
    committee_msg = _make_committee_message(context, results.p1_p3_outputs)
    committee_prompt = prompts.get(COMMITTEE_PROMPT, "")

    committee_tasks = [
        _run_one(member, model, committee_prompt, committee_msg, COMMITTEE_PROMPT, CommitteeOutput)
        for member, model in committee_members
    ]
    log.info("Running 3 committee calls...")
    committee_raw = await asyncio.gather(*committee_tasks)
    results.raw_results.extend(committee_raw)

    for r in committee_raw:
        if r.parsed and isinstance(r.parsed, CommitteeOutput):
            results.p4_outputs.append(r.parsed)

    log.info(f"Committee phase done: {len(results.p4_outputs)}/3 valid outputs")
    return results
