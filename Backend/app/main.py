from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.contestability import apply_contestation
from app.schemas import ContestRequest, ContestResponse, RecommendRequest, RecommendationResponse
from app.service import recommend_from_query

app = FastAPI(
    title="Explainable Travel Recommendation Agent",
    version="0.1.0",
    description="Backend API for explainable and contestable travel recommendations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/recommend", response_model=RecommendationResponse)
def recommend(request: RecommendRequest) -> RecommendationResponse:
    return recommend_from_query(request.query)


@app.post("/api/contest", response_model=ContestResponse)
def contest(request: ContestRequest) -> ContestResponse:
    return apply_contestation(request.previous_response, request.contestation)


@app.get("/api/examples/demo", response_model=RecommendationResponse)
def demo() -> RecommendationResponse:
    query = (
        "I want a 3-day trip to Paris. My budget is EUR 800. "
        "I prefer a quiet hotel near public transport and a direct flight. "
        "Please avoid early morning flights."
    )
    return recommend_from_query(query)
