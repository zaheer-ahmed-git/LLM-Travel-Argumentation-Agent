from fastapi.testclient import TestClient

from app.main import app
from app.preference_extraction import extract_preferences


client = TestClient(app)


DEMO_QUERY = (
    "I want a 3-day trip to Paris. My budget is EUR 800. "
    "I prefer a quiet hotel near public transport and a direct flight. "
    "Please avoid early morning flights."
)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fallback_preference_extraction() -> None:
    preferences = extract_preferences(DEMO_QUERY)
    assert preferences.destination == "Paris"
    assert preferences.duration_days == 3
    assert preferences.budget == 800
    assert "quiet" in preferences.hotel_preferences
    assert "near public transport" in preferences.hotel_preferences
    assert "direct flight" in preferences.flight_preferences


def test_recommend_demo_query_returns_ranked_itineraries() -> None:
    response = client.post("/api/recommend", json={"query": DEMO_QUERY})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["ranked_itineraries"]) >= 3
    assert payload["selected_itinerary"]["hotel_id"] == "hotel_001"
    assert payload["selected_itinerary"]["airline"] == "Air France"
    assert payload["argument_graph"]["nodes"]
    assert payload["explanation"]


def test_contestation_removes_air_france() -> None:
    recommend_response = client.post("/api/recommend", json={"query": DEMO_QUERY})
    assert recommend_response.status_code == 200
    contest_response = client.post(
        "/api/contest",
        json={
            "previous_response": recommend_response.json(),
            "contestation": "I do not want Air France.",
        },
    )
    assert contest_response.status_code == 200
    payload = contest_response.json()
    assert payload["updated_itinerary"]["airline"] != "Air France"
    assert "Air France" in payload["updated_preferences"]["avoid_airlines"]
    assert payload["contested_arguments"]
