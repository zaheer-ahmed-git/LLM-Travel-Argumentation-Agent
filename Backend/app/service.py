from fastapi import HTTPException

from app.argumentation import build_arguments, build_graph, reason_over_arguments
from app.data_loader import load_flights, load_hotels
from app.evaluation import compute_metrics
from app.explanation import generate_explanation
from app.preference_extraction import extract_preferences
from app.recommendation import rank_itineraries
from app.schemas import PreferenceProfile, RecommendationResponse


def recommend_from_query(query: str) -> RecommendationResponse:
    preferences = extract_preferences(query)
    return recommend_from_preferences(preferences)


def recommend_from_preferences(preferences: PreferenceProfile) -> RecommendationResponse:
    hotels = load_hotels()
    flights = load_flights()
    ranked = rank_itineraries(preferences, hotels, flights)
    if not ranked:
        raise HTTPException(status_code=404, detail="No valid itineraries found for the current preferences.")

    selected = ranked[0]
    arguments = build_arguments(selected, hotels, flights)
    graph = build_graph(selected, arguments, hotels, flights)
    reasoning = reason_over_arguments(selected, arguments)
    explanation = generate_explanation(selected, arguments, hotels, flights)
    metrics = compute_metrics(preferences, selected, arguments, explanation)
    return RecommendationResponse(
        preferences=preferences,
        ranked_itineraries=ranked,
        selected_itinerary=selected,
        arguments=arguments,
        argument_graph=graph,
        reasoning=reasoning,
        explanation=explanation,
        metrics=metrics,
    )
