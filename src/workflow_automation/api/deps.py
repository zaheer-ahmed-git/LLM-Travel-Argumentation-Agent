"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from workflow_automation.db.session import get_session as _get_session
from workflow_automation.events.bus import EventBus
from workflow_automation.orchestration.engine import OrchestrationEngine

_event_bus = EventBus()


def get_event_bus() -> EventBus:
    return _event_bus


def get_engine() -> OrchestrationEngine:
    return OrchestrationEngine()


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in _get_session():
        yield session
