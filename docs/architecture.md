# Architecture Notes (Research Summary — 2026)

## Root approach

This project implements **cooperative multi-agent business workflow automation** with a custom orchestration layer on top of the **OpenAI Agents SDK** (Python), exposed through an **event-driven FastAPI** backend with **PostgreSQL-backed agent memory**.

### OpenAI Agents SDK (official)

Sources: [Agents SDK](https://openai.github.io/openai-agents-python/), [Handoffs](https://openai.github.io/openai-agents-python/handoffs/), [Orchestration](https://openai.github.io/openai-agents-python/multi_agent/), [Sessions](https://openai.github.io/openai-agents-python/sessions/), [Tools](https://openai.github.io/openai-agents-python/tools/).

- **Agents**: LLM + instructions + tools; `Runner.run` / `run_sync` / `run_streamed` drive the agent loop.
- **Handoffs**: specialist takes ownership (`handoffs=[...]` / `handoff()`). Good for delegated ownership.
- **Agents as tools**: manager keeps ownership and calls specialists as bounded tools (`agent.as_tool()`). Good for synthesis.
- **Sessions**: client-managed conversation memory (`SQLiteSession` or custom). Do not mix with `conversation_id` / `previous_response_id` in the same run.
- **Tracing / guardrails**: built-in observability and input/output validation.

**Chosen pattern here**: code-orchestrated manager (planner/delegator) + specialist workers + quality reviewer, combining SDK handoffs/tools with a deterministic orchestration layer for role assignment, QC gates, and messaging.

### FastAPI + async PostgreSQL

- One async engine per process; `pool_pre_ping=True`, sensible `pool_recycle`.
- One `AsyncSession` per request; never share across concurrent tasks.
- Keep LLM / external HTTP calls outside long DB transactions.
- SQLAlchemy 2.0 async + asyncpg for agent memory, workflows, tasks, and messages.

### Multi-agent workflow patterns

- **Dynamic role assignment**: map task type / skills to worker roles at runtime.
- **Delegation**: planner decomposes goals; workers execute bounded tasks.
- **Quality control gates**: reviewer scores outputs; fail → rework loop.
- **Inter-agent message bus**: structured events between agents (not raw full transcripts).
- **Context compression**: summarize / truncate payloads before broadcast (~40% less overhead).

### Production-style layout

```
Planner/Delegator → MessageBus → Worker Agents → QC Gate → Memory (Postgres)
                         ↓
                   Event hooks (FastAPI background jobs)
```
