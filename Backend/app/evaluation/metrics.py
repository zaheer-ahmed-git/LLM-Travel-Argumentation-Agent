from app.schemas import Argument, Itinerary, Metrics, PreferenceProfile


def compute_metrics(
    preferences: PreferenceProfile,
    selected: Itinerary,
    arguments: list[Argument],
    explanation: str,
) -> Metrics:
    requested = (
        preferences.hotel_preferences
        + preferences.flight_preferences
        + preferences.constraints
        + (["budget"] if preferences.budget is not None else [])
    )
    preference_coverage = _ratio(len(set(selected.matched_preferences) & set(requested)), len(set(requested)))
    constraint_total = len(preferences.constraints) + len(preferences.avoid_airlines)
    constraint_violations = len(set(preferences.constraints) & set(selected.violated_preferences))
    if selected.airline.lower() in {airline.lower() for airline in preferences.avoid_airlines}:
        constraint_violations += 1
    constraint_satisfaction = 1 - _ratio(constraint_violations, constraint_total)
    argument_coverage = 1.0 if any(argument.type == "support" for argument in arguments) else 0.0
    faithfulness = _faithfulness_score(arguments, explanation)
    return Metrics(
        preference_coverage=round(preference_coverage, 3),
        constraint_satisfaction=round(constraint_satisfaction, 3),
        argument_coverage=round(argument_coverage, 3),
        faithfulness=round(faithfulness, 3),
    )


def _faithfulness_score(arguments: list[Argument], explanation: str) -> float:
    evidence_terms = set()
    for argument in arguments:
        evidence_terms.update(_keywords(argument.evidence))
        evidence_terms.update(_keywords(argument.claim))
    explanation_terms = _keywords(explanation)
    if not explanation_terms:
        return 1.0
    grounded = sum(1 for term in explanation_terms if term in evidence_terms or term in {"recommend", "because", "itinerary", "score", "cost", "main", "tradeoff"})
    return min(1.0, grounded / len(explanation_terms) + 0.25)


def _keywords(value: str) -> set[str]:
    return {word.strip(".,;:()").lower() for word in value.split() if len(word.strip(".,;:()")) > 3}


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator
