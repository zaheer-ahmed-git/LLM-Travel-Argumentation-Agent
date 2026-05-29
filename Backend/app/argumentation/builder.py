from app.schemas import (
    Argument,
    ArgumentGraph,
    Flight,
    GraphEdge,
    GraphNode,
    Hotel,
    Itinerary,
    ReasoningResult,
)


def build_arguments(
    selected: Itinerary,
    hotels: list[Hotel],
    flights: list[Flight],
) -> list[Argument]:
    hotel = _find(hotels, selected.hotel_id)
    flight = _find(flights, selected.flight_id)
    arguments: list[Argument] = []

    if "budget" in selected.matched_preferences:
        arguments.append(
            Argument(
                id="arg_001",
                claim=f"{selected.itinerary_id} fits the stated budget.",
                type="support",
                target_type="itinerary",
                target_id=selected.itinerary_id,
                evidence=f"The estimated total cost is {selected.total_estimated_cost:.0f}.",
                source="score_components",
                weight=0.8,
            )
        )
    elif "budget" in selected.violated_preferences:
        arguments.append(
            Argument(
                id="arg_001",
                claim=f"{selected.itinerary_id} exceeds the stated budget.",
                type="attack",
                target_type="itinerary",
                target_id=selected.itinerary_id,
                evidence=f"The estimated total cost is {selected.total_estimated_cost:.0f}.",
                source="score_components",
                weight=0.7,
            )
        )

    hotel_evidence = (
        f"{hotel.name} is rated {hotel.rating:.1f}, is {hotel.distance_to_station_km:.1f} km "
        f"from public transport, and is described as {hotel.review_summary}"
    )
    arguments.append(
        Argument(
            id="arg_002",
            claim=f"{hotel.name} is suitable for the hotel preferences.",
            type="support" if {"quiet", "near public transport"} & set(selected.matched_preferences) else "attack",
            target_type="hotel",
            target_id=hotel.id,
            evidence=hotel_evidence,
            source="hotel_metadata",
            weight=0.78,
        )
    )

    arguments.append(
        Argument(
            id="arg_003",
            claim=f"{flight.airline} is suitable for the flight preferences.",
            type="support" if flight.layovers == 0 else "attack",
            target_type="flight",
            target_id=flight.id,
            evidence=(
                f"{flight.airline} departs at {flight.departure_time}, arrives at "
                f"{flight.arrival_time}, costs {flight.price:.0f}, and has {flight.layovers} layover(s)."
            ),
            source="flight_metadata",
            weight=0.72 if flight.layovers == 0 else 0.65,
        )
    )

    tradeoffs = [item for item in selected.violated_preferences if item != "budget"]
    if tradeoffs:
        arguments.append(
            Argument(
                id="arg_004",
                claim=f"{selected.itinerary_id} has visible tradeoffs.",
                type="attack",
                target_type="itinerary",
                target_id=selected.itinerary_id,
                evidence=f"Unmet preferences: {', '.join(tradeoffs)}.",
                source="score_components",
                weight=0.45,
            )
        )

    return arguments


def reason_over_arguments(selected: Itinerary, arguments: list[Argument]) -> ReasoningResult:
    accepted = [argument.id for argument in arguments if argument.status == "accepted"]
    rejected = [argument.id for argument in arguments if argument.status == "rejected"]
    conflicts = []
    if any(argument.type == "attack" for argument in arguments):
        conflicts.append("preference_tradeoff")
    return ReasoningResult(
        selected_itinerary_id=selected.itinerary_id,
        accepted_arguments=accepted,
        rejected_arguments=rejected,
        unresolved_conflicts=conflicts,
    )


def build_graph(
    selected: Itinerary,
    arguments: list[Argument],
    hotels: list[Hotel],
    flights: list[Flight],
) -> ArgumentGraph:
    hotel = _find(hotels, selected.hotel_id)
    flight = _find(flights, selected.flight_id)
    nodes = [
        GraphNode(id=selected.itinerary_id, label="Selected itinerary", kind="itinerary"),
        GraphNode(id=hotel.id, label=hotel.name, kind="hotel"),
        GraphNode(id=flight.id, label=flight.airline, kind="flight"),
    ]
    edges = [
        GraphEdge(source=hotel.id, target=selected.itinerary_id, relation="explains"),
        GraphEdge(source=flight.id, target=selected.itinerary_id, relation="explains"),
    ]

    for argument in arguments:
        nodes.append(
            GraphNode(
                id=argument.id,
                label=argument.claim,
                kind=argument.type,
                status=argument.status,
            )
        )
        relation = "supports" if argument.type == "support" else "attacks"
        edges.append(GraphEdge(source=argument.id, target=argument.target_id, relation=relation))

    return ArgumentGraph(nodes=nodes, edges=edges)


def _find(items: list, item_id: str):
    for item in items:
        if item.id == item_id:
            return item
    raise ValueError(f"Could not find item {item_id}")
