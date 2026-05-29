from app.schemas import Flight, Hotel, Itinerary, PreferenceProfile, ScoreComponent


WEIGHTS = {
    "budget_fit": 0.25,
    "hotel_preference_match": 0.22,
    "hotel_rating": 0.16,
    "transport_distance": 0.14,
    "direct_flight": 0.15,
    "departure_time": 0.08,
}


def rank_itineraries(
    preferences: PreferenceProfile,
    hotels: list[Hotel],
    flights: list[Flight],
) -> list[Itinerary]:
    destination = preferences.destination.lower()
    origin = preferences.origin.lower()
    nights = max(preferences.duration_days - 1, 1)
    avoid_airlines = {airline.lower() for airline in preferences.avoid_airlines}

    matching_hotels = [hotel for hotel in hotels if hotel.city.lower() == destination]
    matching_flights = [
        flight
        for flight in flights
        if flight.destination.lower() == destination
        and flight.origin.lower() == origin
        and flight.availability
        and flight.airline.lower() not in avoid_airlines
    ]

    itineraries: list[Itinerary] = []
    counter = 1
    for hotel in matching_hotels:
        for flight in matching_flights:
            total_cost = hotel.price_per_night * nights + flight.price
            components, matched, violated = _score_components(preferences, hotel, flight, total_cost)
            score = round(sum(item.value * item.weight for item in components), 3)
            itineraries.append(
                Itinerary(
                    itinerary_id=f"itinerary_{counter:03d}",
                    score=score,
                    hotel_id=hotel.id,
                    flight_id=flight.id,
                    hotel_name=hotel.name,
                    airline=flight.airline,
                    total_estimated_cost=total_cost,
                    matched_preferences=matched,
                    violated_preferences=violated,
                    score_components=components,
                )
            )
            counter += 1

    return sorted(itineraries, key=lambda item: (-item.score, item.total_estimated_cost))[:6]


def _score_components(
    preferences: PreferenceProfile,
    hotel: Hotel,
    flight: Flight,
    total_cost: float,
) -> tuple[list[ScoreComponent], list[str], list[str]]:
    matched: list[str] = []
    violated: list[str] = []

    budget_score = 1.0
    if preferences.budget is not None:
        if total_cost <= preferences.budget:
            matched.append("budget")
        else:
            violated.append("budget")
            budget_score = max(0.0, 1 - ((total_cost - preferences.budget) / preferences.budget))

    hotel_pref_score = _hotel_preference_score(preferences.hotel_preferences, hotel, matched, violated)
    rating_score = min(hotel.rating / 5, 1)
    transport_score = _transport_score(hotel.distance_to_station_km)
    if "near public transport" in preferences.hotel_preferences:
        if hotel.distance_to_station_km <= 0.6:
            matched.append("near public transport")
        elif "near public transport" not in violated:
            violated.append("near public transport")

    wants_direct = "direct flight" in preferences.flight_preferences
    direct_score = 1.0 if not wants_direct or flight.layovers == 0 else 0.15
    if wants_direct:
        if flight.layovers == 0:
            matched.append("direct flight")
        else:
            violated.append("direct flight")

    avoid_early = "avoid early morning flights" in preferences.constraints
    departure_hour = int(flight.departure_time.split(":")[0])
    departure_score = 1.0
    if avoid_early and departure_hour < 8:
        departure_score = 0.15
        violated.append("avoid early morning flights")
    elif avoid_early:
        matched.append("avoid early morning flights")

    components = [
        ScoreComponent(
            name="budget_fit",
            value=round(budget_score, 3),
            weight=WEIGHTS["budget_fit"],
            reason=f"Estimated cost is {total_cost:.0f} against budget {preferences.budget:.0f}."
            if preferences.budget is not None
            else "No budget was provided.",
        ),
        ScoreComponent(
            name="hotel_preference_match",
            value=round(hotel_pref_score, 3),
            weight=WEIGHTS["hotel_preference_match"],
            reason=f"{hotel.name} matches {len(set(matched) & set(preferences.hotel_preferences))} hotel preferences.",
        ),
        ScoreComponent(
            name="hotel_rating",
            value=round(rating_score, 3),
            weight=WEIGHTS["hotel_rating"],
            reason=f"{hotel.name} is rated {hotel.rating:.1f}/5.",
        ),
        ScoreComponent(
            name="transport_distance",
            value=round(transport_score, 3),
            weight=WEIGHTS["transport_distance"],
            reason=f"{hotel.name} is {hotel.distance_to_station_km:.1f} km from public transport.",
        ),
        ScoreComponent(
            name="direct_flight",
            value=round(direct_score, 3),
            weight=WEIGHTS["direct_flight"],
            reason=f"{flight.airline} flight has {flight.layovers} layover(s).",
        ),
        ScoreComponent(
            name="departure_time",
            value=round(departure_score, 3),
            weight=WEIGHTS["departure_time"],
            reason=f"{flight.airline} departs at {flight.departure_time}.",
        ),
    ]
    return components, _dedupe(matched), _dedupe(violated)


def _hotel_preference_score(
    preferences: list[str],
    hotel: Hotel,
    matched: list[str],
    violated: list[str],
) -> float:
    if not preferences:
        return 1.0

    hits = 0
    tags = set(hotel.tags)
    for preference in preferences:
        normalized = preference.replace(" ", "_")
        is_match = normalized in tags or preference in tags
        if preference == "near public transport":
            is_match = is_match or hotel.distance_to_station_km <= 0.6
        if is_match:
            hits += 1
            matched.append(preference)
        else:
            violated.append(preference)
    return hits / len(preferences)


def _transport_score(distance_km: float) -> float:
    if distance_km <= 0.5:
        return 1.0
    if distance_km <= 1.0:
        return 0.7
    return 0.35


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
