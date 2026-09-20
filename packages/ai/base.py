"""Abstract LLMProvider interface for pluggable AI model providers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel


class LLMResponse(BaseModel):
    raw_text: str
    parsed_json: Optional[Dict[str, Any]] = None
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cached: bool = False

    @property
    def content(self) -> str:
        return self.raw_text

    @property
    def parsed(self) -> Optional[Dict[str, Any]]:
        return self.parsed_json

    @property
    def model_name(self) -> str:
        return self.model



class LLMProvider(ABC):
    """Abstract interface for AI model execution."""

    def __init__(self, name: str, model_name: str):
        self.name = name
        self.model_name = model_name

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Execute text completion or structured JSON extraction."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is configured and reachable."""
        pass
