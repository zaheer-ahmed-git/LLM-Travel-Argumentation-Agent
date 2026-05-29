import json
from functools import lru_cache
from pathlib import Path

from app.schemas import Destination, Flight, Hotel

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(name: str) -> list[dict]:
    path = DATA_DIR / name
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_destinations() -> list[Destination]:
    return [Destination(**item) for item in _load_json("destinations.json")]


@lru_cache(maxsize=1)
def load_hotels() -> list[Hotel]:
    return [Hotel(**item) for item in _load_json("hotels.json")]


@lru_cache(maxsize=1)
def load_flights() -> list[Flight]:
    return [Flight(**item) for item in _load_json("flights.json")]
