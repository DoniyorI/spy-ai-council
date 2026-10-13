from openai import OpenAI

from config.settings import OPENAI_API_KEY
from src.ai.base import CouncilMember
from src.utils.logging_config import log


class OpenAIMember(CouncilMember):
    name = "openai"

    def __init__(self):
        self._client = OpenAI(api_key=OPENAI_API_KEY)

    async def call(self, system_prompt: str, user_message: str, model: str) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            log.error(f"OpenAI call error ({model}): {e}")
            return ""
