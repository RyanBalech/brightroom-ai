"""BrightRoom approved catalogue (Case 02 starter pack) — the single source of truth.

Nothing outside this file may introduce a price, item or condition.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Venue:
    id: str
    name: str
    price: int          # flat price in EUR for one booking
    hours: int          # booking length
    max_people: int
    wheelchair_accessible: bool
    notes: str


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    price: int          # EUR
    per_person: bool    # True = price x headcount, False = flat, added once
    notes: str


VENUES = {
    "V1": Venue("V1", "Studio", 240, 4, 12, False, "4 hours; maximum 12 people; stairs only; Wi-Fi included."),
    "V2": Venue("V2", "Loft", 420, 4, 24, True, "4 hours; maximum 24 people; wheelchair accessible; Wi-Fi included."),
}

SERVICES = {
    "S1": Service("S1", "Coffee break", 8, True, "One coffee break for every attendee."),
    "S2": Service("S2", "Lunch", 18, True,
                  "One lunch for every attendee; vegetarian/vegan on request. No allergen guarantee is supplied."),
    "S3": Service("S3", "Projector", 35, False, "One projector for the booking."),
    "S4": Service("S4", "Facilitator", 280, False, "One facilitator for 2 hours."),
}

# Global rules from the starter pack
MAX_BOOKING_HOURS = 4            # no longer-duration price exists
FACILITATOR_HOURS = 2            # S4 covers 2 hours, flat items can be added only once
MAX_CAPACITY = max(v.max_people for v in VENUES.values())
DIETARY_AVAILABLE = {"vegetarian", "vegan"}   # on request, with lunch only
INCLUDED_FEATURES = {"wi-fi"}                 # included in both venues

RULES_TEXT = [
    "All prices are total amounts in euros; no taxes or other fees are added.",
    "One venue per booking; flat-price items can be added once.",
    "Per-person services cover the full headcount.",
    "No longer-duration price and no discount are available.",
    "Dates require a separate availability check.",
]


def catalogue_as_text() -> str:
    """Plain-text catalogue used inside LLM prompts."""
    lines = ["APPROVED CATALOGUE (EUR, total amounts, no taxes or fees):"]
    for v in VENUES.values():
        lines.append(f"- {v.id} {v.name}: EUR {v.price} per booking. {v.notes}")
    for s in SERVICES.values():
        unit = "/person" if s.per_person else " (flat, once per booking)"
        lines.append(f"- {s.id} {s.name}: EUR {s.price}{unit}. {s.notes}")
    lines.append("RULES: " + " ".join(RULES_TEXT))
    return "\n".join(lines)
