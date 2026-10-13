from google import genai
from google.genai import types

from config.settings import GOOGLE_API_KEY
from src.ai.base import CouncilMember
from src.utils.logging_config import log


class GeminiMember(CouncilMember):
    name = "gemini"

    def __init__(self):
        self._client = genai.Client(api_key=GOOGLE_API_KEY)

    async def call(self, system_prompt: str, user_message: str, model: str) -> str:
        import time
        model_id = model.replace("models/", "")
        try:
            resp = self._client.models.generate_content(
                model=model_id,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            return resp.text or ""
        except Exception as e:
            msg = str(e)
            if "503" in msg or "UNAVAILABLE" in msg:
                log.warning(f"Gemini unavailable ({model}) — skipping (add billing at aistudio.google.com to fix)")
            elif "429" in msg or "quota" in msg.lower():
                log.warning(f"Gemini quota exceeded ({model}) — free tier daily limit hit")
            else:
                log.error(f"Gemini call error ({model}): {e}")
            return ""
