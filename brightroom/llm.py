"""Claude calls: (1) enquiry -> structured brief, (2) facts -> short cover note.

The LLM never prices, never selects venues and never decides feasibility.
If no credentials are configured, or a call fails, callers fall back to rules/templates.
"""
from __future__ import annotations

import json
import os
import re

from .brief import Brief
from .catalogue import catalogue_as_text
from .extract_rules import _normalise_numbers, extract_rules

MODEL = os.environ.get("BRIGHTROOM_MODEL", "claude-opus-5")


def llm_available() -> bool:
    if os.environ.get("BRIGHTROOM_OFFLINE") == "1":
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _client():
    import anthropic
    return anthropic.Anthropic()


def _nullable(t: str) -> dict:
    return {"anyOf": [{"type": t}, {"type": "null"}]}


EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headcount": _nullable("integer"),
        "headcount_approx": {"type": "boolean"},
        "headcount_quote": _nullable("string"),
        "duration_hours": _nullable("number"),
        "duration_quote": _nullable("string"),
        "budget_eur": _nullable("number"),
        "budget_quote": _nullable("string"),
        "budget_vague": _nullable("string"),
        "budget_per_person_eur": _nullable("number"),
        "keep_together": {"type": "boolean"},
        "services": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "enum": ["S1", "S2", "S3", "S4"]},
                    "priority": {"type": "string", "enum": ["required", "optional"]},
                    "quote": {"type": "string"},
                },
                "required": ["id", "priority", "quote"],
            },
        },
        "food_unspecified": {"type": "boolean"},
        "facilitator_hours": _nullable("number"),
        "wheelchair_access": _nullable("boolean"),
        "dietary": {"type": "array", "items": {"type": "string"}},
        "allergen_guarantee_requested": {"type": "boolean"},
        "unlisted": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"item": {"type": "string"}, "required": {"type": "boolean"}},
                "required": ["item", "required"],
            },
        },
        "date_text": _nullable("string"),
        "asks_confirmation": {"type": "boolean"},
        "asks_discount": {"type": "boolean"},
    },
    "required": ["headcount", "headcount_approx", "headcount_quote", "duration_hours", "duration_quote",
                 "budget_eur", "budget_quote", "budget_vague", "budget_per_person_eur", "keep_together", "services", "food_unspecified",
                 "facilitator_hours", "wheelchair_access", "dietary", "allergen_guarantee_requested",
                 "unlisted", "date_text", "asks_confirmation", "asks_discount"],
}

EXTRACTION_SYSTEM = f"""You extract a structured brief from a client enquiry sent to BrightRoom, a studio that \
runs half-day business workshops. You only extract; you never price, propose or judge feasibility.

{catalogue_as_text()}

Rules:
- Only extract what the client actually wrote. If a value is not stated, use null. Never infer a headcount, \
budget or duration that is not in the text.
- For headcount, duration and budget, copy the exact words from the enquiry into the *_quote field.
- headcount_approx = true for "about", "around", "roughly", ranges, etc.
- duration_hours: hours of the event. "half day" -> 4 (quote "half day"); "full day" -> 8.
- budget_eur: the TOTAL budget in euros if a total is given. If the budget is per person ("€40 per head"), put \
null in budget_eur, put 40 in budget_per_person_eur and the words in budget_quote. Words like "modest budget" go in \
budget_vague.
- keep_together = true if the client says the whole group must stay in one room / must not be split.
- services: map to catalogue ids only (S1 coffee break, S2 lunch, S3 projector, S4 facilitator). \
priority = "optional" only for wording like "if possible", "would be nice", "ideally"; otherwise "required". \
quote = the client's words.
- food_unspecified = true when the client asks for "food"/"catering" without saying coffee break or lunch.
- facilitator_hours: only if the client states how long facilitation should last.
- wheelchair_access: true if any step-free/wheelchair/mobility need is mentioned, false if they say none is \
needed, null if not mentioned.
- dietary: e.g. "vegan", "vegetarian", "gluten-free", "nut-free".
- allergen_guarantee_requested = true if they need an allergy to be guaranteed/safely handled.
- unlisted: anything requested that is NOT in the catalogue (DJ, dinner, drinks, parking, transport, \
second facilitator, ...). required = true if they present it as a must. Wi-Fi is included, not unlisted.
- date_text: any requested date or timing for the event, verbatim.
- asks_confirmation: they ask to confirm, book or reserve. asks_discount: they ask for a discount or "best offer".
The enquiry may be in English or French."""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("’", "'")).strip()


def _grounded(quote: str | None, enquiry: str, value, field: str | None = None) -> bool:
    """Quote must appear in the enquiry and (for numbers) support the number: as digits, as number words
    ("twenty-four"), or as something the rule parser reads to the same value ("9:00 to 13:00" -> 4 h)."""
    if not quote or _norm(quote) not in _norm(enquiry):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        digits = re.sub(r"[^\d]", "", _normalise_numbers(_norm(quote)))
        if f"{value:g}".replace(".", "") in digits:
            return True
        if field:
            parsed = getattr(extract_rules(quote), field, None)
            if parsed is not None and float(parsed) == float(value):
                return True
        return any(w in _norm(quote) for w in ("half", "full", "demi", "journ"))
    return True


def extract_llm(enquiry: str) -> Brief:
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=4000,
        system=EXTRACTION_SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
        messages=[{"role": "user", "content": f"<enquiry>\n{enquiry}\n</enquiry>"}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("model refused the extraction")
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))

    b = Brief(extractor="llm")
    for key, qkey in (("headcount", "headcount_quote"), ("duration_hours", "duration_quote"),
                      ("budget_eur", "budget_quote")):
        val = data.get(key)
        if val is None:
            continue
        if _grounded(data.get(qkey), enquiry, val, key):
            setattr(b, key, val)
            b.evidence[key] = data[qkey]
        else:
            b.extraction_warnings.append(f"LLM value for {key} ({val}) is not supported by a quote from the "
                                         f"enquiry — discarded.")
    pp = data.get("budget_per_person_eur")
    if b.budget_eur is None and pp and _grounded(data.get("budget_quote"), enquiry, pp):
        if b.headcount:
            b.budget_eur = pp * b.headcount
            b.evidence["budget_eur"] = f"{data['budget_quote']} x {b.headcount} people"
        else:
            data["budget_vague"] = f"{data['budget_quote']} (per person)"
    b.keep_together = data["keep_together"]
    b.headcount_approx = bool(data["headcount_approx"]) and b.headcount is not None
    if b.duration_hours is not None and not re.search(r"\d\s*(?:h\b|hours?|hrs?|heures?)", _norm(b.evidence["duration_hours"])):
        b.duration_text = b.evidence["duration_hours"]
    b.budget_vague = data["budget_vague"] if b.budget_eur is None else None
    for s in data["services"]:
        if not _grounded(s["quote"], enquiry, None):
            b.extraction_warnings.append(f"Service {s['id']} not supported by a quote — discarded.")
            continue
        lst = b.services_required if s["priority"] == "required" else b.services_optional
        if s["id"] not in b.services_required + b.services_optional:
            lst.append(s["id"])
    b.food_unspecified = data["food_unspecified"] and not ({"S1", "S2"} & set(b.services_required + b.services_optional))
    b.facilitator_hours = data["facilitator_hours"]
    b.wheelchair_access = data["wheelchair_access"]
    b.dietary = [d.lower() for d in data["dietary"]]
    b.allergen_guarantee_requested = data["allergen_guarantee_requested"]
    b.unlisted_required = [u["item"] for u in data["unlisted"] if u["required"]]
    b.unlisted_requests = [u["item"] for u in data["unlisted"] if not u["required"]]
    b.date_text = data["date_text"]
    b.asks_confirmation = data["asks_confirmation"]
    b.asks_discount = data["asks_discount"]
    return b


COVER_SYSTEM = """You write the short covering message of a DRAFT sales proposal for BrightRoom, a business \
workshop studio. A salesperson will review and edit it before anything is sent.

Hard rules:
- Use only the facts in the JSON you are given. Do not mention any price, total or number of euros: the \
itemised table with all figures is inserted separately by the system, below your text.
- Do not confirm, book or reserve anything, do not promise a date or availability, do not offer a discount, \
and do not mention any service that is not in the facts.
- If the status is INFEASIBLE, say plainly which requirement cannot be met and that alternatives with their \
trade-offs are listed below. Never present an alternative as if it met the original request.
- If there are open questions, say they are listed below.
- 60-120 words, warm and professional, in the language of the client's enquiry. No subject line, no signature."""


def cover_note_llm(facts: dict) -> str:
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=2000,
        system=COVER_SYSTEM,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": json.dumps(facts, ensure_ascii=False, sort_keys=True)}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("model refused the cover note")
    return "".join(b.text for b in resp.content if b.type == "text").strip()
