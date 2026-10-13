"""Structured brief: what the client asked for, separated into confirmed / optional / missing."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

SERVICE_KEYS = {"coffee": "S1", "lunch": "S2", "projector": "S3", "facilitator": "S4"}


@dataclass
class Brief:
    # --- core fields (None = not stated) ---
    headcount: int | None = None
    headcount_approx: bool = False          # "about 15", "around 20"
    duration_hours: float | None = None
    duration_text: str | None = None        # e.g. "half day" when interpreted, not stated as a number
    budget_eur: float | None = None
    budget_vague: str | None = None         # e.g. "modest budget" — a constraint we cannot price against
    # --- services: catalogue ids ---
    services_required: list[str] = field(default_factory=list)
    services_optional: list[str] = field(default_factory=list)
    food_unspecified: bool = False          # "with food" — coffee break or lunch?
    facilitator_hours: float | None = None  # if the client says how long they want facilitation
    # --- accessibility & dietary ---
    wheelchair_access: bool | None = None   # None = not mentioned
    dietary: list[str] = field(default_factory=list)       # e.g. ["vegan"]
    allergen_guarantee_requested: bool = False
    # --- things the catalogue cannot promise ---
    unlisted_requests: list[str] = field(default_factory=list)          # optional extras not in catalogue
    unlisted_required: list[str] = field(default_factory=list)          # must-haves not in catalogue
    date_text: str | None = None
    asks_confirmation: bool = False         # "confirm today", "book it"
    asks_discount: bool = False             # "best offer", "discount"
    keep_together: bool = False             # client refuses splitting the group
    # --- provenance ---
    extractor: str = "rules"                # "rules" | "llm" | "llm+rules"
    evidence: dict[str, str] = field(default_factory=dict)  # field -> quote from enquiry
    extraction_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def copy(self, **changes) -> "Brief":
        d = self.to_dict()
        d.update(changes)
        return Brief(**d)
