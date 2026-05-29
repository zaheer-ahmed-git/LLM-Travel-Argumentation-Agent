import json
import re

from app.config import settings
from app.schemas import PreferenceProfile


def extract_preferences(query: str) -> PreferenceProfile:
    if settings.use_llm and settings.openai_api_key:
        try:
            return _extract_with_openai(query)
        except Exception:
            return _fallback_extract(query)
    return _fallback_extract(query)


def _extract_with_openai(query: str) -> PreferenceProfile:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": (
                    "Extract travel preferences as strict JSON matching these keys: "
                    "destination, origin, duration_days, budget, hotel_preferences, "
                    "flight_preferences, constraints, priority_order, avoid_airlines. "
                    "Use empty lists for missing list fields and London as origin if absent."
                ),
            },
            {"role": "user", "content": query},
        ],
    )
    payload = json.loads(response.output_text)
    return PreferenceProfile(**payload)


def _fallback_extract(query: str) -> PreferenceProfile:
    text = query.lower()

    destination = "Paris" if "paris" in text else _title_after(query, "to") or "Paris"
    origin = _title_after(query, "from") or "London"

    duration_match = re.search(r"(\d+)\s*[- ]?\s*day", text)
    duration_days = int(duration_match.group(1)) if duration_match else 3

    budget_match = re.search(r"(?:budget\s*(?:is|of|:)?\s*)?(?:eur|euro|gbp|usd|[$€£])?\s*(\d{2,5})", text)
    budget = float(budget_match.group(1)) if budget_match else None

    hotel_preferences: list[str] = []
    if "quiet" in text:
        hotel_preferences.append("quiet")
    if "public transport" in text or "station" in text or "metro" in text:
        hotel_preferences.append("near public transport")
    if "central" in text or "city center" in text or "city centre" in text:
        hotel_preferences.append("central")
    if "budget hotel" in text or "cheap hotel" in text:
        hotel_preferences.append("budget")

    flight_preferences: list[str] = []
    if "direct" in text or "nonstop" in text or "non-stop" in text:
        flight_preferences.append("direct flight")

    constraints: list[str] = []
    if "avoid early" in text or "not early" in text or "no early" in text:
        constraints.append("avoid early morning flights")

    avoid_airlines = _extract_avoid_airlines(query)

    priority_order = ["budget", "hotel_quality", "transport"]
    if "direct" in text:
        priority_order.append("flight_convenience")

    return PreferenceProfile(
        destination=destination,
        origin=origin,
        duration_days=duration_days,
        budget=budget,
        hotel_preferences=hotel_preferences,
        flight_preferences=flight_preferences,
        constraints=constraints,
        priority_order=priority_order,
        avoid_airlines=avoid_airlines,
    )


def _title_after(query: str, marker: str) -> str | None:
    match = re.search(rf"\b{marker}\s+([A-Z][A-Za-z ]+)", query)
    if not match:
        return None
    value = match.group(1).strip().split(".")[0].split(",")[0]
    words = value.split()
    return " ".join(words[:2])


def _extract_avoid_airlines(query: str) -> list[str]:
    patterns = [
        r"(?:avoid|no|not|do not want|don't want)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)",
    ]
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, query):
            value = match.group(1).strip().rstrip(".")
            if value.lower() not in {"early", "direct"}:
                found.append(value)
    return found
