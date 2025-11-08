"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    agents_ready: bool


class AgentCreate(BaseModel):
    name: str
    role: str
    skills: list[str] = Field(default_factory=list)


class AgentOut(BaseModel):
    id: UUID
    name: str
    role: str
    skills: list
    status: str

    model_config = {"from_attributes": True}


class WorkflowCreate(BaseModel):
    name: str
    goal: str
    description: str = ""


class WorkflowOut(BaseModel):
    id: UUID
    name: str
    description: str
    status: str
    goal: str
    result_summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: int = 1


class TaskOut(BaseModel):
    id: UUID
    workflow_id: UUID
    title: str
    description: str
    assigned_role: str | None
    status: str
    priority: int
    output: str | None = None
    quality_score: float | None = None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: UUID
    workflow_id: UUID
    sender_role: str
    receiver_role: str
    message_type: str
    content: str
    compressed: bool
    original_size: int
    compressed_size: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunRequest(BaseModel):
    goal: str | None = None
    use_llm: bool | None = None
    max_rework: int | None = None


class WorkflowRunResult(BaseModel):
    workflow_id: UUID
    status: str
    assigned_roles: list[str]
    tasks: list[TaskOut]
    quality_passed: bool
    compression_ratio: float
    result_summary: str
    messages_exchanged: int


class MemoryQuery(BaseModel):
    key: str | None = None
    agent_role: str | None = None
    tags: list[str] = Field(default_factory=list)
    limit: int = 5


class MemoryQueryResult(BaseModel):
    entries: list[dict]
    retrieval_ms: float
