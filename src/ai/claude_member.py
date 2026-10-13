import anthropic

from config.settings import ANTHROPIC_API_KEY
from src.ai.base import CouncilMember
from src.utils.logging_config import log


class ClaudeMember(CouncilMember):
    name = "claude"

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    async def call(self, system_prompt: str, user_message: str, model: str) -> str:
        try:
            msg = self._client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return msg.content[0].text
        except Exception as e:
            log.error(f"Claude call error ({model}): {e}")
            return ""
