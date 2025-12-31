"""Run an offline orchestration demo without PostgreSQL."""

from __future__ import annotations

import asyncio
import json

from workflow_automation.config import Settings
from workflow_automation.orchestration.engine import OrchestrationEngine


async def main() -> None:
    settings = Settings(use_llm=False)
    engine = OrchestrationEngine(settings=settings)
    result = await engine.run(
        "Research competitor pricing and write a short recommendation report"
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "assigned_roles": result.assigned_roles,
                "quality_passed": result.quality_passed,
                "compression_ratio": round(result.compression_ratio, 3),
                "messages_exchanged": result.messages_exchanged,
                "summary": result.result_summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
