"""PostgreSQL-backed agent memory with sub-second key/tag retrieval."""

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from workflow_automation.models.orm import MemoryEntry


class MemoryRepository:
    """Store and retrieve agent memory entries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def store(
        self,
        *,
        agent_role: str,
        key: str,
        content: str,
        workflow_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        importance: float = 0.5,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            workflow_id=workflow_id,
            agent_role=agent_role,
            key=key,
            content=content,
            tags=tags or [],
            importance=importance,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def retrieve(
        self,
        *,
        key: str | None = None,
        agent_role: str | None = None,
        tags: list[str] | None = None,
        limit: int = 5,
    ) -> tuple[list[dict[str, Any]], float]:
        started = time.perf_counter()
        stmt: Select[tuple[MemoryEntry]] = select(MemoryEntry)

        if key:
            stmt = stmt.where(MemoryEntry.key.ilike(f"%{key}%"))
        if agent_role:
            stmt = stmt.where(MemoryEntry.agent_role == agent_role)

        # Fetch a slightly larger window, then filter tags in Python for DB portability
        fetch_limit = max(limit * 3, limit)
        stmt = stmt.order_by(MemoryEntry.importance.desc(), MemoryEntry.created_at.desc()).limit(
            fetch_limit
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())

        if tags:
            wanted = {t.lower() for t in tags}
            rows = [
                row
                for row in rows
                if wanted.intersection({str(t).lower() for t in (row.tags or [])})
            ]

        rows = rows[:limit]
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        payload = [
            {
                "id": str(row.id),
                "agent_role": row.agent_role,
                "key": row.key,
                "content": row.content,
                "tags": row.tags,
                "importance": row.importance,
            }
            for row in rows
        ]
        return payload, elapsed_ms
