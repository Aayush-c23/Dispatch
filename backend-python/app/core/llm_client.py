"""Schema-enforced LLM planning with safe deterministic fallbacks.

Supports both OpenAI and Groq backends via the OpenAI-compatible SDK.
Set LLM_PROVIDER in .env to switch between providers.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.relief import (
    DisruptionReplan,
    MissionBriefing,
    ObjectiveCommand,
    OperationalQueryResponse,
    OperationalState,
)

StructuredOutput = TypeVar("StructuredOutput", bound=BaseModel)
Fallback = Callable[[], StructuredOutput]


class LLMClient:
    """Use the Responses API while never making an API key a runtime dependency.

    Each method accepts a deterministic fallback. A successful validated result
    is cached; a missing key, SDK/API exception, refusal, or malformed model
    output returns the relevant cache when available and otherwise that fallback.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client
        self._base_url = base_url
        self._last_plan: ObjectiveCommand | None = None
        self._last_briefing: MissionBriefing | None = None
        self._last_replan: DisruptionReplan | None = None

    @property
    def api_key(self) -> str | None:
        return self._api_key or settings.active_llm_api_key

    @property
    def model(self) -> str:
        return self._model or settings.active_llm_model

    @property
    def base_url(self) -> str | None:
        return self._base_url or settings.active_llm_base_url

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def plan_objective(
        self,
        objective: str,
        state: OperationalState,
        fallback: ObjectiveCommand,
    ) -> ObjectiveCommand:
        prompt = (
            "Create an operational convoy plan. Return only the required structured output. "
            "Use only convoy and request IDs present in the supplied state. Do not invent data.\n\n"
            f"Coordinator objective:\n{objective}\n\nOperational state:\n{self._state_json(state)}"
        )
        return self._request(
            ObjectiveCommand,
            prompt,
            fallback=lambda: fallback,
            cache_name="_last_plan",
        )

    def generate_briefing(
        self,
        objective: str,
        state: OperationalState,
        command: ObjectiveCommand,
        fallback: MissionBriefing,
    ) -> MissionBriefing:
        prompt = (
            "Generate a concise operational Mission Briefing. Return only the required structured output. "
            "Ground every statement in the supplied state and plan. "
            "If multiple alternate routes are present, briefly explain the trade-offs between them in the assessment or predicted bottlenecks.\n\n"
            f"Coordinator objective:\n{objective}\n\nCurrent plan:\n{command.model_dump_json()}\n\n"
            f"Operational state:\n{self._state_json(state)}"
        )
        return self._request(
            MissionBriefing,
            prompt,
            fallback=lambda: fallback,
            cache_name="_last_briefing",
        )

    def replan_after_disruption(
        self,
        disruption_description: str,
        prior_plan: ObjectiveCommand,
        state: OperationalState,
        fallback: DisruptionReplan,
    ) -> DisruptionReplan:
        prompt = (
            "Replan after the stated operational disruption. Return only the required structured output. "
            "Use only entities in the current state and explain what changed in change_summary.\n\n"
            f"Prior plan:\n{prior_plan.model_dump_json()}\n\nDisruption:\n{disruption_description}\n\n"
            f"Current operational state:\n{self._state_json(state)}"
        )
        return self._request(
            DisruptionReplan,
            prompt,
            fallback=lambda: fallback,
            cache_name="_last_replan",
        )

    def answer_operational_query(
        self,
        question: str,
        state: OperationalState,
    ) -> OperationalQueryResponse:
        fallback = OperationalQueryResponse(
            answer="Live state is available, but no LLM operational answer could be generated."
        )
        prompt = (
            "Answer the coordinator's operational question using only the supplied live state. "
            "If the state cannot answer it, say so plainly. Return only the required structured output.\n\n"
            f"Question:\n{question}\n\nLive state:\n{self._state_json(state)}"
        )
        return self._request(OperationalQueryResponse, prompt, fallback=lambda: fallback)

    def _request(
        self,
        schema: type[StructuredOutput],
        prompt: str,
        fallback: Fallback[StructuredOutput],
        cache_name: str | None = None,
    ) -> StructuredOutput:
        if not self.is_configured:
            return fallback()
        try:
            result = self._call_llm(schema, prompt)
        except (Exception, ValidationError):
            cached = getattr(self, cache_name) if cache_name else None
            return cached if cached is not None else fallback()

        if cache_name:
            setattr(self, cache_name, result)
        return result

    def _call_llm(
        self,
        schema: type[StructuredOutput],
        prompt: str,
    ) -> StructuredOutput:
        """Call the LLM via the OpenAI-compatible chat completions API.

        Works with both OpenAI and Groq since Groq exposes the same
        ``/v1/chat/completions`` endpoint.
        """
        client = self._get_client()
        json_schema_str = json.dumps(schema.model_json_schema())
        system_msg = (
            "You are a humanitarian logistics planning assistant. "
            "Respond ONLY with valid JSON matching this schema — no markdown, no commentary:\n"
            f"{json_schema_str}"
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = response.choices[0].message.content
        return schema.model_validate_json(raw)

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    @staticmethod
    def _state_json(state: OperationalState) -> str:
        return json.dumps(state.model_dump(mode="json"), separators=(",", ":"))


llm_client = LLMClient()
