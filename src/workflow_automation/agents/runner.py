"""Runtime that executes specialists via OpenAI Agents SDK or local fallback."""

from __future__ import annotations

import logging

from workflow_automation.agents.factory import AgentFactory, WorkerResult
from workflow_automation.config import Settings

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(self, settings: Settings, factory: AgentFactory | None = None) -> None:
        self.settings = settings
        self.factory = factory or AgentFactory(model=settings.openai_model)
        self._sdk_agents = None
        if settings.use_llm and settings.openai_api_key:
            self._sdk_agents = self.factory.build_sdk_agents()

    @property
    def llm_enabled(self) -> bool:
        return bool(self._sdk_agents)

    async def run_worker(
        self,
        role: str,
        task_title: str,
        task_description: str,
        goal: str,
    ) -> WorkerResult:
        if not self._sdk_agents:
            return self.factory.local_worker(role, task_title, task_description, goal)

        agent = self._sdk_agents.get(role) or self._sdk_agents.get("analyst")
        prompt = (
            f"Workflow goal: {goal}\n"
            f"Task: {task_title}\n"
            f"Details: {task_description}\n"
            "Produce a concise, actionable result."
        )
        try:
            from agents import Runner

            result = await Runner.run(agent, prompt)
            return WorkerResult(role=role, content=str(result.final_output), used_llm=True)
        except Exception as exc:  # noqa: BLE001 — fall back for portfolio demos
            logger.warning("LLM worker failed (%s); using local fallback", exc)
            return self.factory.local_worker(role, task_title, task_description, goal)
