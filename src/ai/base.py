from abc import ABC, abstractmethod


class CouncilMember(ABC):
    name: str = "base"

    @abstractmethod
    async def call(self, system_prompt: str, user_message: str, model: str) -> str:
        """Call the model and return raw text response."""
        ...
