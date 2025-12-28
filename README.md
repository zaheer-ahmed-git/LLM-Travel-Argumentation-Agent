# Multi-Agent Workflow Automation

Cooperative agent system that automates business workflows with a **custom orchestration layer** for delegation, quality control, and inter-agent communication.

Built with **OpenAI Agents SDK**, **FastAPI**, **PostgreSQL**, and **Python**.

## Highlights

| Capability | Approach |
|---|---|
| Dynamic role assignment | Planner maps goals to specialist roles at runtime |
| Context compression | Extractive compression cuts communication overhead (~40%) |
| Event-driven API | FastAPI endpoints + background job hooks |
| Agent memory | PostgreSQL-backed memory with sub-second retrieval |
| Quality control | Reviewer gate with rework loops |
| Orchestration | Custom message bus + OpenAI Agents SDK handoffs/tools |

## Architecture

```
Planner / Delegator
        │
        ▼
  Message Bus ──► Worker Agents (research / analysis / writing)
        │                    │
        │                    ▼
        └──────────► Quality Reviewer (QC gate)
                           │
                           ▼
                 PostgreSQL agent memory
```

See [docs/architecture.md](docs/architecture.md) for research notes (Agents SDK handoffs vs agents-as-tools, async SQLAlchemy patterns, multi-agent QC).

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

# Optional Postgres
docker compose up -d

# Offline demo (no API key required)
python scripts/run_demo.py

# API
uvicorn workflow_automation.api.main:app --app-dir src --reload
```

### API endpoints

- `GET /health` — readiness
- `GET /agents/roles` — available cooperative roles
- `POST /agents` / `GET /agents` — register / list agents
- `POST /workflows` / `GET /workflows` — create / list workflows
- `POST /workflows/{id}/tasks` — attach manual tasks
- `POST /workflows/{id}/run` — run orchestration (sync)
- `POST /workflows/{id}/run-async` — queue event-driven job hook
- `GET /workflows/{id}/messages` — inter-agent messages
- `POST /memory/query` — retrieve agent memory
- `GET /events` — recent workflow events

## Project layout

```
src/workflow_automation/
  agents/          # OpenAI Agents SDK factory + runtime
  orchestration/   # roles, message bus, QC, engine
  compression/     # context compression
  db/              # async SQLAlchemy + memory repo
  events/          # event bus hooks
  api/             # FastAPI app
  models/          # ORM + Pydantic schemas
docs/              # architecture research notes
scripts/           # offline demo
tests/             # pytest (no API key required)
```

## Configuration

Copy `.env.example` to `.env`. Keep `USE_LLM=false` for local offline runs; set `OPENAI_API_KEY` and `USE_LLM=true` to enable live Agents SDK workers.

## Tests

```bash
pytest
```

## License

MIT
