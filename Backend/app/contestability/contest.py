import re

from app.schemas import Argument, ContestResponse, PreferenceProfile, RecommendationResponse
from app.service import recommend_from_preferences


def apply_contestation(previous: RecommendationResponse, contestation: str) -> ContestResponse:
    updated_preferences = previous.preferences.model_copy(deep=True)
    avoided_airlines = _parse_avoided_airlines(contestation)
    for airline in avoided_airlines:
        if airline.lower() not in {item.lower() for item in updated_preferences.avoid_airlines}:
            updated_preferences.avoid_airlines.append(airline)

    updated = recommend_from_preferences(updated_preferences)
    contested = _mark_contested(previous.arguments, avoided_airlines, previous.selected_itinerary.airline)
    reason = _reason(previous.selected_itinerary.itinerary_id, updated.selected_itinerary.itinerary_id, avoided_airlines)

    return ContestResponse(
        updated_preferences=updated.preferences,
        updated_itinerary=updated.selected_itinerary,
        contested_arguments=contested,
        argument_graph=updated.argument_graph,
        explanation=updated.explanation,
        reason_for_update=reason,
        ranked_itineraries=updated.ranked_itineraries,
        metrics=updated.metrics,
    )


def _parse_avoided_airlines(text: str) -> list[str]:
    patterns = [
        r"(?:avoid|no|not|do not want|don't want)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)",
    ]
    results: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = match.group(1).strip().rstrip(".")
            if value.lower() not in {"early", "direct", "morning"}:
                results.append(value)
    return results


def _mark_contested(arguments: list[Argument], airlines: list[str], selected_airline: str) -> list[Argument]:
    targets = {airline.lower() for airline in airlines} or {selected_airline.lower()}
    contested = []
    for argument in arguments:
        evidence = f"{argument.claim} {argument.evidence}".lower()
        if any(airline in evidence for airline in targets):
            contested.append(argument.model_copy(update={"status": "contested"}))
    return contested


def _reason(previous_id: str, updated_id: str, airlines: list[str]) -> str:
    if airlines:
        names = ", ".join(airlines)
        if previous_id != updated_id:
            return f"The previous recommendation changed because flights from {names} were excluded."
        return f"Flights from {names} were excluded, but the same itinerary remained the top valid option."
    return "The contestation was recorded, but no specific airline constraint could be parsed."
