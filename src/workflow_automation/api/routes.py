"""HTTP routes for workflows, agents, tasks, memory, and events."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from workflow_automation import __version__
from workflow_automation.api.deps import get_db, get_engine, get_event_bus
from workflow_automation.config import get_settings
from workflow_automation.db.memory import MemoryRepository
from workflow_automation.events.bus import EventBus
from workflow_automation.models.orm import AgentRecord, MessageRecord, TaskRecord, WorkflowRecord
from workflow_automation.models.schemas import (
    AgentCreate,
    AgentOut,
    HealthResponse,
    MemoryQuery,
    MemoryQueryResult,
    MessageOut,
    TaskCreate,
    TaskOut,
    WorkflowCreate,
    WorkflowOut,
    WorkflowRunRequest,
    WorkflowRunResult,
)
from workflow_automation.orchestration.engine import OrchestrationEngine
from workflow_automation.orchestration.roles import DEFAULT_ROLES

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        database="configured" if settings.database_url else "missing",
        agents_ready=True,
    )


@router.get("/agents/roles")
async def list_roles() -> list[dict]:
    return [
        {"role": r.role, "skills": list(r.skills), "description": r.description}
        for r in DEFAULT_ROLES
    ]


@router.post("/agents", response_model=AgentOut)
async def create_agent(
    payload: AgentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentRecord:
    agent = AgentRecord(name=payload.name, role=payload.role, skills=payload.skills)
    db.add(agent)
    await db.flush()
    return agent


@router.get("/agents", response_model=list[AgentOut])
async def list_agents(db: Annotated[AsyncSession, Depends(get_db)]) -> list[AgentRecord]:
    result = await db.execute(select(AgentRecord).order_by(AgentRecord.created_at.desc()))
    return list(result.scalars().all())


@router.post("/workflows", response_model=WorkflowOut)
async def create_workflow(
    payload: WorkflowCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    events: Annotated[EventBus, Depends(get_event_bus)],
) -> WorkflowRecord:
    workflow = WorkflowRecord(
        name=payload.name,
        goal=payload.goal,
        description=payload.description,
        status="pending",
    )
    db.add(workflow)
    await db.flush()
    await events.emit("workflow.created", {"workflow_id": str(workflow.id), "name": workflow.name})
    return workflow


@router.get("/workflows", response_model=list[WorkflowOut])
async def list_workflows(db: Annotated[AsyncSession, Depends(get_db)]) -> list[WorkflowRecord]:
    result = await db.execute(select(WorkflowRecord).order_by(WorkflowRecord.created_at.desc()))
    return list(result.scalars().all())


@router.get("/workflows/{workflow_id}", response_model=WorkflowOut)
async def get_workflow(
    workflow_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowRecord:
    workflow = await db.get(WorkflowRecord, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.post("/workflows/{workflow_id}/tasks", response_model=TaskOut)
async def add_task(
    workflow_id: uuid.UUID,
    payload: TaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskRecord:
    workflow = await db.get(WorkflowRecord, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    task = TaskRecord(
        workflow_id=workflow_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
    )
    db.add(task)
    await db.flush()
    return task


@router.get("/workflows/{workflow_id}/tasks", response_model=list[TaskOut])
async def list_tasks(
    workflow_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TaskRecord]:
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.workflow_id == workflow_id)
    )
    return list(result.scalars().all())


@router.get("/workflows/{workflow_id}/messages", response_model=list[MessageOut])
async def list_messages(
    workflow_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MessageRecord]:
    result = await db.execute(
        select(MessageRecord)
        .where(MessageRecord.workflow_id == workflow_id)
        .order_by(MessageRecord.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunResult)
async def run_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowRunRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    engine: Annotated[OrchestrationEngine, Depends(get_engine)],
    events: Annotated[EventBus, Depends(get_event_bus)],
) -> WorkflowRunResult:
    workflow = await db.get(WorkflowRecord, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow.status = "running"
    await events.emit("workflow.started", {"workflow_id": str(workflow.id)})

    goal = payload.goal or workflow.goal
    result = await engine.run(goal=goal, max_rework=payload.max_rework)

    # Persist tasks + compressed messages
    task_outs: list[TaskOut] = []
    for task_state in result.tasks:
        record = TaskRecord(
            workflow_id=workflow.id,
            title=task_state.title,
            description=task_state.description,
            assigned_role=task_state.assigned_role,
            status=task_state.status,
            output=task_state.output,
            quality_score=task_state.quality_score,
        )
        db.add(record)
        await db.flush()
        task_outs.append(TaskOut.model_validate(record))

    for message in engine.bus.messages:
        db.add(
            MessageRecord(
                workflow_id=workflow.id,
                sender_role=message.sender_role,
                receiver_role=message.receiver_role,
                message_type=message.message_type,
                content=message.content,
                compressed=message.compressed,
                original_size=message.original_size,
                compressed_size=message.compressed_size,
            )
        )

    memory = MemoryRepository(db)
    await memory.store(
        agent_role="planner",
        key=f"workflow:{workflow.id}:summary",
        content=result.result_summary,
        workflow_id=workflow.id,
        tags=["summary", "workflow"],
        importance=0.9,
    )

    workflow.status = result.status
    workflow.result_summary = result.result_summary
    await events.emit(
        "workflow.completed",
        {
            "workflow_id": str(workflow.id),
            "status": result.status,
            "quality_passed": result.quality_passed,
        },
    )

    return WorkflowRunResult(
        workflow_id=workflow.id,
        status=result.status,
        assigned_roles=result.assigned_roles,
        tasks=task_outs,
        quality_passed=result.quality_passed,
        compression_ratio=result.compression_ratio,
        result_summary=result.result_summary,
        messages_exchanged=result.messages_exchanged,
    )


@router.post("/workflows/{workflow_id}/run-async")
async def run_workflow_async(
    workflow_id: uuid.UUID,
    payload: WorkflowRunRequest,
    background: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    events: Annotated[EventBus, Depends(get_event_bus)],
) -> dict:
    """Event-driven style endpoint: enqueue a background orchestration job."""
    workflow = await db.get(WorkflowRecord, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    async def _job() -> None:
        await events.emit(
            "workflow.queued",
            {
                "workflow_id": str(workflow_id),
                "goal": payload.goal or workflow.goal,
            },
        )

    background.add_task(_job)
    workflow.status = "queued"
    return {"workflow_id": str(workflow_id), "status": "queued"}


@router.get("/events")
async def list_events(events: Annotated[EventBus, Depends(get_event_bus)]) -> list[dict]:
    return [
        {
            "id": e.id,
            "name": e.name,
            "payload": e.payload,
            "created_at": e.created_at.isoformat(),
        }
        for e in events.history()
    ]


@router.post("/memory/query", response_model=MemoryQueryResult)
async def query_memory(
    payload: MemoryQuery,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemoryQueryResult:
    repo = MemoryRepository(db)
    entries, elapsed = await repo.retrieve(
        key=payload.key,
        agent_role=payload.agent_role,
        tags=payload.tags,
        limit=payload.limit,
    )
    return MemoryQueryResult(entries=entries, retrieval_ms=elapsed)
