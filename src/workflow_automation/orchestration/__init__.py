"""Custom orchestration: roles, delegation, message bus, QC gates."""

from workflow_automation.orchestration.engine import OrchestrationEngine, OrchestrationResult
from workflow_automation.orchestration.message_bus import AgentMessage, MessageBus
from workflow_automation.orchestration.quality import QualityGate, QualityVerdict
from workflow_automation.orchestration.roles import RoleAssigner, RoleProfile

__all__ = [
    "OrchestrationEngine",
    "OrchestrationResult",
    "AgentMessage",
    "MessageBus",
    "QualityGate",
    "QualityVerdict",
    "RoleAssigner",
    "RoleProfile",
]
