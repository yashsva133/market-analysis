"""AI Router with automatic fallback, aggressive caching, and token auditing."""
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

from packages.common.config import settings
from packages.common.logging import get_logger
from .base import LLMProvider, LLMResponse
from .rule_provider import RuleProvider
from .gemini_provider import GeminiProvider

logger = get_logger(__name__)


class AIRouter:
    """Dispatches tasks to the configured AI provider with caching and execution auditing."""

    def __init__(self):
        self.rule_provider = RuleProvider()
        self.gemini_provider = GeminiProvider()
        self.active_provider_name = settings.AI_ACTIVE_PROVIDER
        
        # Fast in-memory deterministic response cache
        # input_hash -> LLMResponse
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            "calls_total": 0,
            "cache_hits": 0,
            "tokens_in": 0,
            "tokens_out": 0,
        }

    def get_provider(self) -> LLMProvider:
        """Resolves the active provider or falls back."""
        if self.active_provider_name == "gemini":
            return self.gemini_provider
        return self.rule_provider

    def compute_input_hash(self, prompt: str, task: str) -> str:
        """Compute stable SHA-256 hash for aggressive cache checking."""
        content = f"{task}:{prompt.strip()}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def execute_task(
        self,
        task: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        db_session: Optional[Any] = None,
    ) -> LLMResponse:
        """Executes task with aggressive caching and token audit tracking."""
        self._stats["calls_total"] += 1
        input_hash = self.compute_input_hash(prompt, task)

        # 1. Check in-memory cache
        if settings.AI_CACHE_ENABLED and input_hash in self._cache:
            self._stats["cache_hits"] += 1
            cached_entry = self._cache[input_hash]
            logger.info(f"AI Cache Hit for task '{task}' (hash: {input_hash[:8]}). Zero tokens consumed.")
            return LLMResponse(
                raw_text=cached_entry.get("raw_text") or cached_entry.get("content") or "",
                parsed_json=cached_entry.get("parsed_json") or (cached_entry.get("parsed").model_dump(mode="json") if hasattr(cached_entry.get("parsed"), "model_dump") else cached_entry.get("parsed")),
                provider=cached_entry.get("provider", "cache"),
                model=cached_entry.get("model") or cached_entry.get("model_name", "cached"),
                tokens_in=0,
                tokens_out=0,
                latency_ms=0,
                cached=True,
            )

        # 2. Check Database cache if db_session provided
        if settings.AI_CACHE_ENABLED and db_session:
            try:
                from sqlalchemy import select
                from packages.common.models import AIRun, AIOutput
                run_res = await db_session.execute(
                    select(AIRun).where(AIRun.input_hash == input_hash, AIRun.status == "SUCCESS").limit(1)
                )
                existing_run = run_res.scalar_one_or_none()
                if existing_run:
                    out_res = await db_session.execute(
                        select(AIOutput).where(AIOutput.ai_run_id == existing_run.id).limit(1)
                    )
                    out = out_res.scalar_one_or_none()
                    if out:
                        self._stats["cache_hits"] += 1
                        raw_str = json.dumps(out.structured_output) if isinstance(out.structured_output, dict) else str(out.structured_output)
                        return LLMResponse(
                            raw_text=raw_str,
                            parsed_json=out.structured_output if isinstance(out.structured_output, dict) else None,
                            provider="db_cache",
                            model=existing_run.model or "cache",
                            tokens_in=0,
                            tokens_out=0,
                            latency_ms=0,
                            cached=True,
                        )
            except Exception as e:
                logger.debug(f"DB cache lookup skipped: {e}")

        # 3. Dispatch to Provider
        provider = self.get_provider()
        if not await provider.is_available():
            logger.info(f"Provider '{provider.name}' not available. Falling back to RuleProvider.")
            provider = self.rule_provider

        start_time = time.time()
        status = "SUCCESS"
        error_msg = None
        response = None

        try:
            response = await provider.complete(
                prompt=prompt,
                system_instruction=system_instruction,
                schema=schema,
            )
        except Exception as e:
            logger.warning(f"Error during {provider.name} execution: {e}. Falling back to RuleProvider.")
            try:
                response = await self.rule_provider.complete(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    schema=schema,
                )
            except Exception as fallback_e:
                status = "FAILED"
                error_msg = str(fallback_e)
                raise fallback_e

        latency_ms = int((time.time() - start_time) * 1000)
        if response:
            response.latency_ms = latency_ms

            # Update stats
            self._stats["tokens_in"] += response.tokens_in
            self._stats["tokens_out"] += response.tokens_out

            # Store in cache
            if settings.AI_CACHE_ENABLED:
                self._cache[input_hash] = {
                    "content": response.content,
                    "parsed": response.parsed,
                    "model_name": response.model_name,
                    "raw_text": response.raw_text,
                    "parsed_json": response.parsed_json,
                    "provider": response.provider,
                    "model": response.model,
                }

            # Audit to Database if session provided
            if db_session:
                try:
                    import uuid
                    from packages.common.models import AIRun, AIOutput
                    run_id = uuid.uuid4()
                    db_run = AIRun(
                        id=run_id,
                        provider=provider.name,
                        model=response.model_name,
                        task=task,
                        input_hash=input_hash,
                        started_at=datetime.now(timezone.utc),
                        finished_at=datetime.now(timezone.utc),
                        status=status,
                        tokens_in=response.tokens_in,
                        tokens_out=response.tokens_out,
                        cached=False,
                        error=error_msg,
                    )
                    db_session.add(db_run)
                    if response.parsed and isinstance(response.parsed, BaseModel):
                        out_record = AIOutput(
                            ai_run_id=run_id,
                            task=task,
                            object_type="task_result",
                            object_id=run_id,
                            schema_version="1.0",
                            structured_output=response.parsed.model_dump(mode="json"),
                            evidence_ids=[],
                        )
                        db_session.add(out_record)
                    await db_session.commit()
                except Exception as audit_err:
                    logger.debug(f"Audit log write failed: {audit_err}")
                    await db_session.rollback()

        return response

    def get_stats(self) -> Dict[str, Any]:
        """Return cumulative token and cache efficiency statistics."""
        return dict(self._stats)


# Global AI router singleton
ai_router = AIRouter()
