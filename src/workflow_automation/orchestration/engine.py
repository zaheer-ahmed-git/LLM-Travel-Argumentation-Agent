"""Custom orchestration engine for delegation, messaging, and QC loops."""

from __future__ import annotations

from dataclasses import dataclass, field

from workflow_automation.agents.runner import AgentRuntime
from workflow_automation.compression.compressor import ContextCompressor
from workflow_automation.config import Settings, get_settings
from workflow_automation.orchestration.message_bus import MessageBus
from workflow_automation.orchestration.quality import QualityGate, QualityVerdict
from workflow_automation.orchestration.roles import RoleAssigner


@dataclass
class TaskState:
    title: str
    description: str
    assigned_role: str
    status: str = "pending"
    output: str | None = None
    quality_score: float | None = None


@dataclass
class OrchestrationResult:
    status: str
    assigned_roles: list[str]
    tasks: list[TaskState]
    quality_passed: bool
    quality: QualityVerdict
    compression_ratio: float
    result_summary: str
    messages_exchanged: int
    meta: dict = field(default_factory=dict)


class OrchestrationEngine:
    """Coordinates planner → workers → reviewer with a message bus."""

    def __init__(
        self,
        settings: Settings | None = None,
        runtime: AgentRuntime | None = None,
        assigner: RoleAssigner | None = None,
        bus: MessageBus | None = None,
        quality_gate: QualityGate | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.runtime = runtime or AgentRuntime(self.settings)
        self.assigner = assigner or RoleAssigner()
        self.compressor = ContextCompressor(
            max_chars=self.settings.compression_max_chars,
            target_ratio=self.settings.compression_target_ratio,
        )
        self.bus = bus or MessageBus(compressor=self.compressor)
        self.quality_gate = quality_gate or QualityGate(
            pass_threshold=self.settings.qc_pass_threshold
        )

    async def run(self, goal: str, max_rework: int | None = None) -> OrchestrationResult:
        max_cycles = max_rework if max_rework is not None else self.settings.max_rework_cycles
        raw_tasks = self.assigner.decompose_goal(goal)
        tasks: list[TaskState] = []

        self.bus.publish(
            sender_role="planner",
            receiver_role="*",
            content=f"New workflow goal received: {goal}. Decomposing into specialist tasks.",
            message_type="broadcast",
        )

        for item in raw_tasks:
            role = self.assigner.assign(item["title"], item["description"])
            tasks.append(
                TaskState(
                    title=item["title"],
                    description=item["description"],
                    assigned_role=role,
                    status="assigned",
                )
            )
            self.bus.publish(
                sender_role="planner",
                receiver_role=role,
                content=(
                    f"Delegating task '{item['title']}'. "
                    f"Description: {item['description']}. Please deliver a structured result."
                ),
                message_type="delegation",
            )

        quality = QualityVerdict(0.0, False, "Not evaluated")
        for cycle in range(max_cycles + 1):
            for task in tasks:
                task.status = "running"
                result = await self.runtime.run_worker(
                    task.assigned_role, task.title, task.description, goal
                )
                task.output = result.content
                task.status = "completed"
                self.bus.publish(
                    sender_role=task.assigned_role,
                    receiver_role="reviewer",
                    content=result.content,
                    message_type="result",
                )

            combined = "\n\n".join(
                f"## {t.assigned_role}: {t.title}\n{t.output}" for t in tasks if t.output
            )
            quality = self.quality_gate.evaluate(combined, goal)
            for task in tasks:
                task.quality_score = quality.score

            self.bus.publish(
                sender_role="reviewer",
                receiver_role="planner",
                content=f"QC score={quality.score:.2f}. {quality.feedback}",
                message_type="quality",
            )
            if quality.passed:
                break
            if cycle < max_cycles:
                self.bus.publish(
                    sender_role="planner",
                    receiver_role="*",
                    content=f"Rework cycle {cycle + 1}: improve coverage and structure.",
                    message_type="rework",
                )

        summary = self._summarize(goal, tasks, quality)
        status = "completed" if quality.passed else "needs_review"
        roles = sorted({t.assigned_role for t in tasks})
        return OrchestrationResult(
            status=status,
            assigned_roles=roles,
            tasks=tasks,
            quality_passed=quality.passed,
            quality=quality,
            compression_ratio=self.bus.compression_ratio(),
            result_summary=summary,
            messages_exchanged=len(self.bus.messages),
            meta={"rework_cycles": max_cycles, "llm_enabled": self.runtime.llm_enabled},
        )

    @staticmethod
    def _summarize(goal: str, tasks: list[TaskState], quality: QualityVerdict) -> str:
        lines = [
            f"Goal: {goal}",
            f"Quality: {quality.score:.2f} ({'pass' if quality.passed else 'fail'})",
            "Task outputs:",
        ]
        for task in tasks:
            snippet = (task.output or "")[:220].replace("\n", " ")
            lines.append(f"- [{task.assigned_role}] {task.title}: {snippet}")
        return "\n".join(lines)
