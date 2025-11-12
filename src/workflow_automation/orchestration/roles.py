"""Dynamic role assignment for cooperative workflow agents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RoleProfile:
    role: str
    skills: tuple[str, ...]
    description: str


DEFAULT_ROLES: tuple[RoleProfile, ...] = (
    RoleProfile(
        role="planner",
        skills=("planning", "decomposition", "delegation"),
        description="Breaks goals into tasks and assigns specialists.",
    ),
    RoleProfile(
        role="researcher",
        skills=("research", "analysis", "summarization"),
        description="Gathers and synthesizes background information.",
    ),
    RoleProfile(
        role="analyst",
        skills=("analysis", "metrics", "reporting"),
        description="Turns findings into structured business insights.",
    ),
    RoleProfile(
        role="writer",
        skills=("writing", "documentation", "communication"),
        description="Drafts stakeholder-facing deliverables.",
    ),
    RoleProfile(
        role="reviewer",
        skills=("quality", "review", "compliance"),
        description="Scores outputs and enforces quality gates.",
    ),
)


class RoleAssigner:
    """Assigns worker roles from task keywords and available skills."""

    def __init__(self, roles: tuple[RoleProfile, ...] | None = None) -> None:
        self.roles = roles or DEFAULT_ROLES
        self._workers = [r for r in self.roles if r.role not in {"planner", "reviewer"}]

    def available_roles(self) -> list[str]:
        return [r.role for r in self.roles]

    def assign(self, task_title: str, task_description: str = "") -> str:
        text = f"{task_title} {task_description}".lower()
        best_role = self._workers[0].role if self._workers else "analyst"
        best_score = -1.0
        for profile in self._workers:
            score = 0.0
            for skill in profile.skills:
                if skill in text:
                    score += 2.0
                # soft match on role name
                if profile.role in text:
                    score += 1.5
            if score > best_score:
                best_score = score
                best_role = profile.role
        return best_role

    def decompose_goal(self, goal: str) -> list[dict[str, str]]:
        """Heuristic task decomposition used when LLM planner is disabled."""
        goal_l = goal.lower()
        tasks: list[dict[str, str]] = []
        if any(k in goal_l for k in ("research", "market", "competitor", "data")):
            tasks.append(
                {
                    "title": "Research background",
                    "description": f"Collect facts and constraints for: {goal}",
                }
            )
        tasks.append(
            {
                "title": "Analyze requirements",
                "description": f"Extract actionable requirements from: {goal}",
            }
        )
        if any(k in goal_l for k in ("report", "brief", "write", "document", "proposal")):
            tasks.append(
                {
                    "title": "Draft deliverable",
                    "description": f"Write a concise deliverable for: {goal}",
                }
            )
        else:
            tasks.append(
                {
                    "title": "Produce recommendation",
                    "description": f"Recommend next actions for: {goal}",
                }
            )
        return tasks
