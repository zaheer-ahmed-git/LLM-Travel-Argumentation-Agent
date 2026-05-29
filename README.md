# Explainable Travel Recommendation Agent

An early-stage travel planning prototype that recommends hotel and flight combinations, explains why a recommendation was chosen, and lets the user challenge part of the reasoning.

The project is built around a simple idea: travel recommendations should not feel like a black box. If the system picks a hotel and flight, it should also show the preferences it understood, the evidence it used, the tradeoffs it accepted, and what changes when the user disagrees.

## What This Project Solves

Most travel recommendation demos stop at ranking options. That is useful, but it leaves a few important questions unanswered:

- Why did this itinerary win?
- Which user preferences were actually satisfied?
- Which preferences were ignored or traded off?
- What evidence supports the recommendation?
- Can the user challenge a bad assumption and get a revised result?

This repository explores those questions with a small but complete backend pipeline. It takes a natural-language travel request, extracts structured preferences, scores candidate hotels and flights, builds argument-style explanations, and supports a basic contestation flow.

The current frontend is a Next.js workspace scaffold. The backend already contains the main recommendation logic and API surface; the UI is the next major piece of work.

## Current Status

This is a research-oriented MVP, not a production booking app.

Implemented:

- FastAPI backend with health, recommendation, contestation, and demo endpoints
- Local JSON datasets for Paris hotels, flights, destinations, and sample reviews
- Preference extraction with a deterministic fallback and optional OpenAI-powered extraction
- Itinerary ranking with explainable score components
- Structured support and attack arguments
- Argument graph data returned through the API
- Natural-language explanations grounded in selected evidence
- Contestation flow for excluding airlines such as "I do not want Air France"
- Basic metrics for preference coverage, constraint satisfaction, argument coverage, and explanation faithfulness
- Pytest coverage for the demo flow

Still in progress:

- Real frontend experience for entering requests and viewing results
- Graph visualization for the argument structure
- Richer contestation handling beyond airline exclusions
- Broader destination and supplier data
- More formal argumentation semantics

## Repository Structure

```text
TravelAgentReco/
|-- Backend/
|   |-- app/
|   |   |-- argumentation/          # Builds arguments and graph edges
|   |   |-- contestability/         # Handles user challenges
|   |   |-- evaluation/             # Computes quality metrics
|   |   |-- explanation/            # Generates recommendation text
|   |   |-- preference_extraction/  # Converts user text into preferences
|   |   |-- recommendation/         # Scores and ranks itineraries
|   |   |-- config.py
|   |   |-- data_loader.py
|   |   |-- main.py
|   |   `-- schemas.py
|   |-- data/                       # Mock travel data
|   |-- examples/                   # Example requests and contestation notes
|   |-- tests/                      # API and flow tests
|   |-- main.py                     # Local uvicorn entrypoint
|   `-- pyproject.toml
|
|-- Frontend/
|   `-- frontendtravelagent/        # Next.js app workspace
|
|-- ProjectPlan.md
|-- implementationPlan.md
`-- README.md
```

## Architecture

The backend follows a small pipeline:

```text
User query
   |
Preference extraction
   |
Candidate loading from JSON
   |
Hotel + flight itinerary scoring
   |
Argument generation
   |
Argument graph construction
   |
Reasoning summary + explanation + metrics
   |
API response
```

For contestation, the flow starts from a previous recommendation response:

```text
Previous recommendation + user challenge
   |
Parse new constraint
   |
Mark affected arguments as contested
   |
Re-rank valid itineraries
   |
Return updated recommendation and reason for change
```

The current contestation implementation focuses on airline exclusions. For example, if the selected itinerary uses Air France and the user says "I do not want Air France", the backend adds Air France to `avoid_airlines`, re-runs the recommendation pipeline, and returns a new top itinerary when one is available.

## Backend

The backend lives in [`Backend`](Backend/) and is built with:

- Python 3.13+
- FastAPI
- Pydantic
- pydantic-settings
- OpenAI SDK, optional
- pytest
- uvicorn

### API Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Basic service health check |
| `POST` | `/api/recommend` | Generate ranked itineraries from a natural-language request |
| `POST` | `/api/contest` | Challenge a previous recommendation and re-rank |
| `GET` | `/api/examples/demo` | Return the built-in Paris demo recommendation |

### Recommendation Request

```json
{
  "query": "I want a 3-day trip to Paris. My budget is EUR 800. I prefer a quiet hotel near public transport and a direct flight. Please avoid early morning flights."
}
```

The response includes:

- `preferences`: structured preferences extracted from the query
- `ranked_itineraries`: scored candidate hotel and flight combinations
- `selected_itinerary`: the highest-ranked itinerary
- `arguments`: support and attack arguments for the chosen option
- `argument_graph`: nodes and edges suitable for visualization
- `reasoning`: accepted arguments and unresolved conflicts
- `explanation`: a readable summary of why the itinerary was selected
- `metrics`: lightweight quality indicators

### Contestation Request

Use the full response from `POST /api/recommend` as `previous_response`, then add a challenge:

```json
{
  "previous_response": {
    "...": "full recommendation response"
  },
  "contestation": "I do not want Air France."
}
```

The response returns the updated preference profile, updated itinerary, contested arguments, a refreshed graph, and a short reason explaining why the result changed.

## Frontend

The frontend workspace lives in [`Frontend/frontendtravelagent`](Frontend/frontendtravelagent/). It currently contains the default Next.js app shell with:

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- ESLint

The intended UI is a focused travel-agent interface:

- A request form for natural-language trip preferences
- Ranked itinerary cards with cost, score, hotel, and flight details
- A readable explanation panel
- Argument graph visualization
- Contestation input for challenging the recommendation
- Before-and-after comparison after a contestation

Until that UI is implemented, the backend can be exercised directly through FastAPI docs, curl, or tests.

## Local Setup

Clone the repository, then install the backend and frontend separately.

### Backend Setup

From the repository root:

```bash
cd Backend
python -m venv .venv
```

Activate the environment.

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the backend package and dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Create a local environment file:

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

The default `.env.example` keeps LLM usage disabled:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_LLM=false
```

That mode is enough to run the demo and tests. To use OpenAI for preference extraction, set `USE_LLM=true` and provide `OPENAI_API_KEY`.

### Run The Backend

From `Backend/`:

```bash
python main.py
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive docs are available at:

```text
http://127.0.0.1:8000/docs
```

### Try A Recommendation

```bash
curl -X POST http://127.0.0.1:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d @examples/recommend_request.json
```

Or open:

```text
http://127.0.0.1:8000/api/examples/demo
```

### Frontend Setup

In a second terminal:

```bash
cd Frontend/frontendtravelagent
npm install
npm run dev
```

The Next.js app runs at:

```text
http://localhost:3000
```

At the moment, this shows the scaffolded Next.js page. The backend already allows requests from `http://localhost:3000` and `http://127.0.0.1:3000` through CORS.

## Development Workflow

### Run Backend Tests

From `Backend/`:

```bash
pytest
```

The current tests cover:

- `/health`
- fallback preference extraction
- the main recommendation demo
- contesting an airline and receiving a changed recommendation

### Run Frontend Checks

From `Frontend/frontendtravelagent/`:

```bash
npm run lint
npm run build
```

The frontend is still mostly scaffolded, so backend tests are the stronger signal right now.

## Implementation Notes

### Preference Extraction

`Backend/app/preference_extraction/extractor.py` has two paths:

- LLM extraction, used when `USE_LLM=true` and an API key is present
- deterministic fallback extraction, used by default for local development and reproducible tests

The fallback parser is intentionally small. It recognizes the demo-style request patterns, including destination, duration, budget, hotel preferences, direct-flight preference, early-flight avoidance, and airline exclusions.

### Scoring

`Backend/app/recommendation/scoring.py` creates hotel-flight combinations and scores them with weighted components:

- budget fit
- hotel preference match
- hotel rating
- distance to public transport
- direct flight preference
- departure time

Each score component carries a reason string, which keeps the ranking inspectable and makes the explanation easier to audit.

### Argumentation

`Backend/app/argumentation/builder.py` turns the selected itinerary into structured arguments. Arguments have a claim, type, target, evidence, source, weight, and status.

The graph returned by the API is deliberately simple: itineraries, hotels, flights, and arguments are nodes; `supports`, `attacks`, and `explains` are edges. That shape should be easy to render later with a library such as React Flow.

### Explanation

`Backend/app/explanation/generator.py` builds the final explanation from accepted arguments and candidate metadata. The goal is not flashy prose; the goal is a recommendation that stays tied to the evidence the system actually used.

### Contestability

`Backend/app/contestability/contest.py` handles a user challenge after a recommendation. In the current version, it can parse airline avoidance requests, mark matching arguments as contested, update preferences, and run the ranking pipeline again.

### Evaluation

`Backend/app/evaluation/metrics.py` returns lightweight quality metrics:

- `preference_coverage`
- `constraint_satisfaction`
- `argument_coverage`
- `faithfulness`

These are not meant to be final academic metrics, but they give the prototype a measurable backbone and a clear place to improve.

## Data

The backend uses local JSON files in `Backend/data/`:

- `destinations.json`
- `hotels.json`
- `flights.json`
- `sample_reviews.json`

The current dataset is intentionally small and Paris-focused. That keeps the project easy to run, test, and explain. A larger dataset should preserve the same schema or introduce import/normalization code rather than changing the core pipeline.

## Roadmap

Near-term:

- Replace the scaffolded frontend with a working recommendation UI
- Add a graph view for the returned argument graph
- Show score components and preference matches in the interface
- Add a contestation panel and updated-result comparison
- Expand tests around parser edge cases and contestation behavior

Medium-term:

- Support more contestation types, such as budget changes, hotel location concerns, layover objections, or accessibility needs
- Add more destinations and richer mock data
- Use `sample_reviews.json` more directly as evidence
- Improve reasoning over support and attack arguments instead of only summarizing them
- Add saved example responses for demos and regression testing

Longer-term:

- Connect to real travel or review APIs behind a clean data adapter
- Add persistent sessions if the app needs trip history
- Introduce a more formal argumentation framework
- Evaluate explanation faithfulness and usefulness with a stronger methodology
- Prepare deployment for a hosted demo

Keep the project easy to inspect. This is a demo where clarity matters as much as cleverness.


