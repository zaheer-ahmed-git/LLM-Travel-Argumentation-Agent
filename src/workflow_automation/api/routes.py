"""HTTP routes for workflows, agents, tasks, memory, and events."""
from fastapi import APIRouter
from workflow_automation import __version__
from workflow_automation.models.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, database="configured", agents_ready=True)
