from app.schemas import Argument, Flight, Hotel, Itinerary


def generate_explanation(
    selected: Itinerary,
    arguments: list[Argument],
    hotels: list[Hotel],
    flights: list[Flight],
) -> str:
    hotel = _find(hotels, selected.hotel_id)
    flight = _find(flights, selected.flight_id)
    supports = [argument for argument in arguments if argument.type == "support" and argument.status == "accepted"]
    attacks = [argument for argument in arguments if argument.type == "attack" and argument.status == "accepted"]

    support_text = "; ".join(argument.evidence.rstrip(".") for argument in supports[:3])
    if not support_text:
        support_text = "the selected option has the best available score from the current evidence"

    explanation = (
        f"I recommend {hotel.name} with the {flight.airline} flight because {support_text}. "
        f"The itinerary score is {selected.score:.2f} and the estimated total cost is "
        f"{selected.total_estimated_cost:.0f}."
    )
    if attacks:
        tradeoff_text = "; ".join(argument.evidence.rstrip(".") for argument in attacks[:2])
        explanation += f" The main tradeoff is: {tradeoff_text}."
    return explanation


def _find(items: list, item_id: str):
    for item in items:
        if item.id == item_id:
            return item
    raise ValueError(f"Could not find item {item_id}")
