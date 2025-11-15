"""Agent definitions for planner, workers, and quality reviewer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkerResult:
    role: str
    content: str
    used_llm: bool = False


class AgentFactory:
    """Build OpenAI Agents SDK agents when available; otherwise local stubs."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    def build_sdk_agents(self) -> dict[str, Any] | None:
        try:
            from agents import Agent, handoff
        except ImportError:
            return None

        researcher = Agent(
            name="Researcher",
            handoff_description="Research and summarize business context.",
            instructions=(
                "You gather relevant facts, constraints, and sources for a workflow goal. "
                "Return a concise bullet summary."
            ),
            model=self.model,
        )
        analyst = Agent(
            name="Analyst",
            handoff_description="Analyze requirements and produce insights.",
            instructions=(
                "You analyze requirements and produce structured insights with clear next steps."
            ),
            model=self.model,
        )
        writer = Agent(
            name="Writer",
            handoff_description="Draft stakeholder-facing deliverables.",
            instructions=(
                "You write clear, actionable deliverables for business stakeholders."
            ),
            model=self.model,
        )
        reviewer = Agent(
            name="Reviewer",
            handoff_description="Quality-review workflow outputs.",
            instructions=(
                "You score outputs for clarity, goal coverage, and actionability. "
                "Return a short verdict and improvement notes."
            ),
            model=self.model,
        )
        planner = Agent(
            name="Planner",
            instructions=(
                "You are the workflow planner/delegator. Decompose the user goal, "
                "then hand off to the best specialist. Prefer short structured plans."
            ),
            model=self.model,
            handoffs=[
                handoff(researcher),
                handoff(analyst),
                handoff(writer),
                handoff(reviewer),
            ],
        )
        return {
            "planner": planner,
            "researcher": researcher,
            "analyst": analyst,
            "writer": writer,
            "reviewer": reviewer,
        }

    def local_worker(self, role: str, task_title: str, task_description: str, goal: str) -> WorkerResult:
        """Deterministic worker used in tests and offline mode."""
        templates = {
            "researcher": (
                f"Research summary for '{goal}'. Key findings: constraints identified, "
                f"stakeholders mapped, risks listed. Focus task: {task_title}. "
                f"Details: {task_description}. Recommend validating assumptions next."
            ),
            "analyst": (
                f"Analysis for '{goal}'. Requirements extracted from '{task_title}'. "
                f"Metrics: impact, effort, risk. Recommendation: prioritize high-impact actions. "
                f"Context: {task_description}."
            ),
            "writer": (
                f"Deliverable draft for '{goal}'.\n"
                f"1. Summary of '{task_title}'.\n"
                f"2. Proposed actions with owners.\n"
                f"3. Next checkpoint.\n"
                f"Notes: {task_description}."
            ),
        }
        content = templates.get(
            role,
            (
                f"Completed '{task_title}' for goal '{goal}'. "
                f"Output covers requirements, risks, and next steps. {task_description}"
            ),
        )
        return WorkerResult(role=role, content=content, used_llm=False)
