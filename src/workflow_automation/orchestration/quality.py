"""Quality-control gates for workflow outputs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityVerdict:
    score: float
    passed: bool
    feedback: str


class QualityGate:
    """Deterministic QC scoring with optional LLM enrichment later."""

    def __init__(self, pass_threshold: float = 0.7) -> None:
        self.pass_threshold = pass_threshold

    def evaluate(self, output: str, goal: str) -> QualityVerdict:
        text = (output or "").strip()
        if not text:
            return QualityVerdict(0.0, False, "Empty output.")

        score = 0.35
        # Length heuristic: neither too short nor absurdly long
        length = len(text)
        if 120 <= length <= 4000:
            score += 0.25
        elif length >= 40:
            score += 0.1

        goal_tokens = {t for t in goal.lower().split() if len(t) > 3}
        overlap = sum(1 for t in goal_tokens if t in text.lower())
        if goal_tokens:
            score += min(0.3, 0.3 * (overlap / max(len(goal_tokens), 1)))

        structure_markers = ("1.", "-", "*", "summary", "recommend", "next")
        if any(m in text.lower() for m in structure_markers):
            score += 0.1

        score = min(1.0, round(score, 3))
        passed = score >= self.pass_threshold
        feedback = (
            "Quality gate passed."
            if passed
            else "Quality gate failed: strengthen goal coverage and structure."
        )
        return QualityVerdict(score=score, passed=passed, feedback=feedback)
