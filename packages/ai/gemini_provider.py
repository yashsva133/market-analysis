"""Pluggable Google Gemini Provider adapter with multi-model fallback."""
import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
import httpx

from packages.common.config import settings
from packages.common.logging import get_logger
from .base import LLMProvider, LLMResponse

logger = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini API Provider adapter with automatic model fallback."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(name="gemini", model_name=model or settings.GEMINI_MODEL)
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.candidate_models = [
            self.model_name,
            "gemini-flash-lite-latest",
            "gemini-flash-latest",
            "gemini-pro-latest",
        ]

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        if not await self.is_available():
            raise RuntimeError("Gemini Provider is not configured or missing API key.")

        start_time = time.time()
        
        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if schema:
            generation_config["responseMimeType"] = "application/json"

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        last_error = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            for model_name in self.candidate_models:
                clean_model = model_name if model_name.startswith("models/") else f"models/{model_name}"
                url = f"{self.base_url}/{clean_model}:generateContent?key={self.api_key}"
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_text = ""
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                raw_text = parts[0].get("text", "")
                        
                        parsed_json = None
                        if raw_text:
                            try:
                                parsed_json = json.loads(raw_text)
                            except Exception:
                                clean_text = raw_text.strip()
                                if clean_text.startswith("```json"):
                                    clean_text = clean_text[7:]
                                if clean_text.startswith("```"):
                                    clean_text = clean_text[3:]
                                if clean_text.endswith("```"):
                                    clean_text = clean_text[:-3]
                                try:
                                    parsed_json = json.loads(clean_text.strip())
                                except Exception:
                                    pass

                        latency = int((time.time() - start_time) * 1000)
                        return LLMResponse(
                            raw_text=raw_text,
                            parsed_json=parsed_json,
                            provider=self.name,
                            model=model_name,
                            latency_ms=latency,
                        )
                    elif resp.status_code in (404, 503, 429):
                        logger.warning(f"Gemini model {model_name} returned {resp.status_code}. Trying next candidate...")
                        last_error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        break
                except Exception as ex:
                    last_error = str(ex)
                    continue

        logger.error(f"All Gemini model candidates exhausted. Last error: {last_error}")
        raise RuntimeError(f"Gemini API failure: {last_error}")
