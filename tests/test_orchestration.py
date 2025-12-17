"""Tests for role assignment, compression, QC, and orchestration."""

import pytest

from workflow_automation.compression.compressor import ContextCompressor
from workflow_automation.config import Settings
from workflow_automation.orchestration.engine import OrchestrationEngine
from workflow_automation.orchestration.quality import QualityGate
from workflow_automation.orchestration.roles import RoleAssigner


def test_role_assigner_picks_researcher_for_research_tasks():
    assigner = RoleAssigner()
    role = assigner.assign("Research market competitors", "Need research and summarization")
    assert role == "researcher"


def test_role_assigner_decomposes_report_goal():
    tasks = RoleAssigner().decompose_goal("Write a market research report")
    titles = " ".join(t["title"].lower() for t in tasks)
    assert "research" in titles or "analyze" in titles
    assert len(tasks) >= 2


def test_context_compression_reduces_overhead():
    text = (
        "Basically we really just need to deliver a summary. "
        "In order to actually proceed, the team must approve the next action. "
        "Kind of important metric: reduce risk before the deadline. "
        "Sort of long filler text that repeats itself without adding value. " * 3
    )
    result = ContextCompressor(max_chars=400, target_ratio=0.6).compress(text)
    assert result.compressed is True
    assert result.compressed_size < result.original_size
    assert result.ratio <= 0.7


def test_quality_gate_passes_structured_output():
    gate = QualityGate(pass_threshold=0.7)
    goal = "Prepare vendor evaluation recommendation with clear next steps"
    output = (
        "Summary of vendor evaluation recommendation.\n"
        "1. Score vendors on risk and impact.\n"
        "2. Recommend shortlist and next checkpoint.\n"
        "- Action: approve pilot with owner."
    )
    verdict = gate.evaluate(output, goal)
    assert verdict.passed is True
    assert verdict.score >= 0.7


def test_quality_gate_fails_empty():
    verdict = QualityGate().evaluate("", "any goal")
    assert verdict.passed is False


@pytest.mark.asyncio
async def test_orchestration_engine_runs_offline():
    settings = Settings(use_llm=False, openai_api_key="")
    engine = OrchestrationEngine(settings=settings)
    result = await engine.run(
        "Research competitor pricing and write a short recommendation report"
    )
    assert result.messages_exchanged >= 3
    assert result.assigned_roles
    assert result.compression_ratio <= 1.0
    assert result.result_summary
    assert result.status in {"completed", "needs_review"}
