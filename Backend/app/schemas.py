from typing import Any, Literal

from pydantic import BaseModel, Field


class PreferenceProfile(BaseModel):
    destination: str
    origin: str = "London"
    duration_days: int = Field(ge=1)
    budget: float | None = Field(default=None, ge=0)
    hotel_preferences: list[str] = Field(default_factory=list)
    flight_preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    priority_order: list[str] = Field(default_factory=list)
    avoid_airlines: list[str] = Field(default_factory=list)


class Destination(BaseModel):
    id: str
    city: str
    country: str
    currency: str
    notes: str


class Hotel(BaseModel):
    id: str
    name: str
    city: str
    price_per_night: float
    rating: float
    distance_to_station_km: float
    review_summary: str
    tags: list[str]


class Flight(BaseModel):
    id: str
    airline: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    price: float
    layovers: int
    availability: bool


class ScoreComponent(BaseModel):
    name: str
    value: float
    weight: float
    reason: str


class Itinerary(BaseModel):
    itinerary_id: str
    score: float
    hotel_id: str
    flight_id: str
    hotel_name: str
    airline: str
    total_estimated_cost: float
    matched_preferences: list[str]
    violated_preferences: list[str]
    score_components: list[ScoreComponent]


class Argument(BaseModel):
    id: str
    claim: str
    type: Literal["support", "attack"]
    target_type: Literal["itinerary", "hotel", "flight", "preference"]
    target_id: str
    evidence: str
    source: str
    weight: float = Field(ge=0, le=1)
    status: Literal["accepted", "rejected", "contested"] = "accepted"


class GraphNode(BaseModel):
    id: str
    label: str
    kind: str
    status: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: Literal["supports", "attacks", "explains", "contests"]


class ArgumentGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ReasoningResult(BaseModel):
    selected_itinerary_id: str
    accepted_arguments: list[str]
    rejected_arguments: list[str]
    unresolved_conflicts: list[str]


class Metrics(BaseModel):
    preference_coverage: float
    constraint_satisfaction: float
    argument_coverage: float
    faithfulness: float


class RecommendRequest(BaseModel):
    query: str = Field(min_length=8, max_length=4000)


class RecommendationResponse(BaseModel):
    preferences: PreferenceProfile
    ranked_itineraries: list[Itinerary]
    selected_itinerary: Itinerary
    arguments: list[Argument]
    argument_graph: ArgumentGraph
    reasoning: ReasoningResult
    explanation: str
    metrics: Metrics


class ContestRequest(BaseModel):
    previous_response: RecommendationResponse
    contestation: str = Field(min_length=3, max_length=1000)


class ContestResponse(BaseModel):
    updated_preferences: PreferenceProfile
    updated_itinerary: Itinerary
    contested_arguments: list[Argument]
    argument_graph: ArgumentGraph
    explanation: str
    reason_for_update: str
    ranked_itineraries: list[Itinerary]
    metrics: Metrics


JsonDict = dict[str, Any]
