"""FastAPI application factory for Multi-Agent Workflow Automation."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from workflow_automation import __version__
from workflow_automation.api.routes import router
from workflow_automation.config import get_settings
from workflow_automation.db.session import dispose_engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    # Best-effort schema init; API can still start for health checks if DB is down
    try:
        await init_db()
        app.state.db_ready = True
    except Exception:  # noqa: BLE001
        app.state.db_ready = False
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Agent Workflow Automation",
        description=(
            "Cooperative agent system automating business workflows with a custom "
            "orchestration layer for delegation, quality control, and inter-agent communication."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
