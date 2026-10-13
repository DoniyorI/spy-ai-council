import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.utils.logging_config import log

T = TypeVar("T", bound=BaseModel)


def _strip_fences(text: str) -> str:
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_block(text: str) -> str:
    # Find first { ... } block, handling nested braces
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def _fix_trailing_commas(text: str) -> str:
    # Remove trailing commas before } or ]
    return re.sub(r",\s*([}\]])", r"\1", text)


def parse_strict(raw_text: str, schema: Type[T]) -> T | None:
    if not raw_text:
        return None

    cleaned = _strip_fences(raw_text)
    cleaned = _extract_json_block(cleaned)
    cleaned = _fix_trailing_commas(cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        log.warning(f"JSON parse error: {e} | raw snippet: {raw_text[:200]}")
        return None

    try:
        return schema.model_validate(data)
    except ValidationError as e:
        log.warning(f"Schema validation error: {e} | data: {data}")
        return None
