"""Simple async event bus for FastAPI background hooks."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4


@dataclass
class WorkflowEvent:
    name: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


Handler = Callable[[WorkflowEvent], Awaitable[None] | None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._history: list[WorkflowEvent] = []

    def on(self, event_name: str, handler: Handler) -> None:
        self._handlers[event_name].append(handler)

    async def emit(self, name: str, payload: dict[str, Any] | None = None) -> WorkflowEvent:
        event = WorkflowEvent(name=name, payload=payload or {})
        self._history.append(event)
        for handler in list(self._handlers.get(name, [])) + list(self._handlers.get("*", [])):
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
        return event

    def history(self, limit: int = 50) -> list[WorkflowEvent]:
        return self._history[-limit:]
