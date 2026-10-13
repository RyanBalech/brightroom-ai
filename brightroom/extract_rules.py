"""Deterministic (regex) extractor: works offline, and cross-checks the LLM extractor.

Deliberately conservative: when it is not sure, it leaves a field empty so the
engine asks a question instead of guessing. Handles simple English and French.
"""
from __future__ import annotations

import re

from .brief import Brief

APPROX = r"(?:about|around|approximately|approx\.?|roughly|~|circa|some|up to|environ|à peu près)"
PEOPLE = (r"(?:people|persons?|pax|participants?|attendees?|colleagues?|employees?|guests?|staff|"
          r"members|ppl|personnes?|collaborateurs?|salariés?)")

SERVICE_PATTERNS = {
    "S1": r"coff?ee?\b|caf[ée]\b|pause[- ]caf",
    "S2": r"lunch|d[ée]jeuner|repas|\bmeal",
    "S3": r"project[oe]r|projecteur|beamer",
    "S4": r"facilitat|animat(?:eur|rice)|moderator|someone to (?:run|lead)",
}
FOOD_VAGUE = r"\bfood\b|catering|snacks?|nourriture|something to eat|refreshments"
OPTIONAL_MARKERS = (r"if possible|would be nice|nice to have|optional|maybe|perhaps|ideally|if budget allows|"
                    r"if affordable|si possible|[ée]ventuellement|could also|a plus")
NEGATION = (r"(?:\bno|without|don'?t need|do not need|not need|sans|pas de|(?:sort|bring|organi[sz]e|arrange|handle)"
            r"(?: out)? (?:our|their) own|(?:our|their) own)\s+(?:\w+\s+){0,2}?")

UNLISTED = {
    r"\bdj\b|music|musique": "DJ / music",
    r"dinner|d[îi]ner|evening meal": "Dinner",
    r"breakfast|petit[- ]d[ée]jeuner": "Breakfast",
    r"drinks|ap[ée]ritif|ap[ée]ro|cocktail|wine|beer|alcohol|champagne": "Drinks / alcohol",
    r"transport|shuttle|\bbus\b|taxi": "Transport",
    r"parking": "Parking",
    r"photograph": "Photographer",
    r"hotel|accommodation|overnight|h[ée]bergement": "Accommodation",
    r"microphone|\bmic\b|sound system|speakers\b|sono": "Sound system / microphone",
    r"whiteboard|flipchart|paperboard": "Whiteboard / flipchart",
    r"video[- ]?conferenc|zoom|hybrid|livestream|streaming|visio": "Video-conferencing / hybrid set-up",
    r"translat|interpret": "Interpreter / translation",
    r"printing|printed": "Printing",
    r"\bgifts?\b|goodies|swag": "Gifts",
    r"escape game|cooking class|team[- ]building activit": "Team-building activity",
    r"second facilitator|two facilitators|2 facilitators": "Second facilitator",
    r"two projectors|2 projectors": "Second projector",
}
DIETARY = {
    r"vegan|v[ée]g[ée]talien|végan": "vegan",
    r"vegetarian|veggie|v[ée]g[ée]tarien": "vegetarian",
    r"gluten": "gluten-free",
    r"halal": "halal",
    r"kosher|casher": "kosher",
    r"lactose|dairy": "lactose-free",
    r"\bnuts?\b|peanut": "nut-free",
}
ALLERGY = r"allerg|nut[- ]free|gluten[- ]free|coeliac|celiac|lactose[- ]free|anaphyla"
STRONG = r"guarantee|must|need|severe|strict|essential|required|garanti"
WHEELCHAIR = (r"wheelchair|step[- ]free|accessib|reduced mobility|mobility|fauteuil|\bpmr\b|"
              r"\blift\b|elevator|ascenseur|crutch|walking aid|walker|"
              r"(?:can'?t|cannot|can not|unable to|not able to) (?:do|climb|use|manage|take) (?:the )?stairs|"
              r"no stairs|avoid (?:the )?stairs|pas d'escalier")
NO_ACCESS_NEED = (r"no (?:special )?access(?:ibility)? (?:needs|requirements|issues)|no wheelchair|"
                  r"(?:nobody|no one|none of us|no-one)[^.]{0,30}(?:mobility|wheelchair|access)|"
                  r"no mobility (?:issues|needs|problems)|"
                  r"stairs (?:are|is) (?:totally |completely |perfectly )?(?:fine|ok|okay|no problem|not a problem)|"
                  r"stairs (?:aren'?t|are not) (?:a |an )?(?:problem|issue)|(?:fine|ok) with stairs|"
                  r"escaliers? ne pose(?:nt)? (?:aucun|pas de) probl[èe]me|escaliers? (?:ok|pas de souci)")
DATE = (r"\b(today|tomorrow|tonight|next (?:week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
        r"this (?:week|month|monday|tuesday|wednesday|thursday|friday)|"
        r"on (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
        r"\d{1,2}(?:st|nd|rd|th)? (?:of )?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*|"
        r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w* \d{1,2}|"
        r"\d{1,2}/\d{1,2}(?:/\d{2,4})?|demain|aujourd'hui|mois prochain|semaine prochaine)\b")
CONFIRM = r"confirm|book (?:it|this|the|us)|reserve|reservation|guarantee the date|confirmer|r[ée]server"
DISCOUNT = (r"discount|best offer|best price|best deal|cheaper deal|special price|reduction|r[ée]duction|"
            r"remise|\d+\s*% off|meilleur prix|meilleure offre")
VAGUE_BUDGET = (r"((?:modest|small|tight|limited|reasonable|low|smallish|petit|serr[ée]|raisonnable)\s+budget|"
                r"budget (?:is )?(?:modest|small|tight|limited)|not too expensive|cheap|pas trop cher)")


NUMBER_WORDS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "a dozen": 12, "dozen": 12,
    "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
    "douze": 12, "quinze": 15, "vingt": 20, "trente": 30,
}


def _normalise_numbers(t: str) -> str:
    """'twenty-two' -> 22, 'fifteen' -> 15, '1.2k' -> 1200 (only standalone words)."""
    t = re.sub(r"\b(twenty|thirty|forty|fifty)[- ](one|two|three|four|five|six|seven|eight|nine)\b",
               lambda m: str(NUMBER_WORDS[m.group(1)] + NUMBER_WORDS[m.group(2)]), t)
    for w in sorted(NUMBER_WORDS, key=len, reverse=True):
        t = re.sub(rf"\b{w}\b(?!-)", str(NUMBER_WORDS[w]), t)
    t = re.sub(r"(\d+(?:[.,]\d+)?)\s*k\b", lambda m: str(int(float(m.group(1).replace(",", ".")) * 1000)), t)
    return t


def _clauses(text: str) -> list[str]:
    return [c.strip() for c in re.split(r"[.;!?\n]+|,\s*but\s+|\bbut\b", text) if c.strip()]


def _parse_amount(raw: str) -> float | None:
    s = raw.strip().replace(" ", " ").replace("\xa0", " ")
    s = re.sub(r"(?<=\d)[ ,](?=\d{3}\b)", "", s)          # 1,500 / 1 500 -> 1500
    s = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", s)             # 1.500 -> 1500
    s = s.replace(",", ".")
    m = re.match(r"\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def _find_budget(t: str) -> tuple[float | None, str | None]:
    money = re.finditer(
        r"(?:€|eur\b|euros?\b)\s*(\d[\d ,. \xa0]*\d|\d)|(\d[\d ,. \xa0]*\d|\d)\s*(?:€|eur\b|euros?\b|k€)", t)
    for m in money:
        before = t[max(0, m.start() - 25):m.start()]
        if "%" in t[m.end():m.end() + 2] or re.search(r"discount|off\b|remise", before):
            continue
        val = _parse_amount(m.group(1) or m.group(2))
        if val is not None:
            if "k€" in m.group(0):
                val *= 1000
            return val, m.group(0).strip()
    m = re.search(r"(?:budget|spend|max(?:imum)?)\s*(?:of|is|:|=|de|up to)?\s*(\d[\d ,.]*\d|\d)\b(?!\s*(?:people|hours|h\b|%))", t)
    if m:
        return _parse_amount(m.group(1)), m.group(0).strip()
    return None, None


def extract_rules(enquiry: str) -> Brief:
    t = _normalise_numbers(enquiry.lower().replace("’", "'"))
    b = Brief(extractor="rules")
    clauses = _clauses(t)

    # --- headcount ---
    pats = [
        rf"(?P<approx>{APPROX}\s+)?(?P<n>\d{{1,4}})\s*(?:-|to)?\s*(?:\d{{1,4}}\s*)?{PEOPLE}",
        rf"(?:we are|we're|we will be|we'll be|nous sommes|nous serons|group of|team of|groupe de)\s+(?P<approx>{APPROX}\s+)?(?P<n>\d{{1,4}})",
        rf"(?P<approx>{APPROX}\s+)?(?P<n>\d{{1,4}}) of us\b",
        rf"\bfor (?P<approx>{APPROX}\s+)?(?P<n>\d{{1,4}})\b(?!\s*(?:hours?|hrs?|h\b|heures?|€|eur|euros?|%|minutes?|days?))",
    ]
    # Sub-groups ("2 colleagues use wheelchairs") are always smaller than the group: keep the largest.
    matches = [m for p in pats for m in re.finditer(p, t)]
    if matches:
        m = max(matches, key=lambda m: int(m.group("n")))
        b.headcount = int(m.group("n"))
        b.headcount_approx = bool(m.group("approx")) or bool(re.search(r"\d+\s*(?:-|to)\s*\d+\s*" + PEOPLE, t))
        b.evidence["headcount"] = m.group(0).strip()

    # --- duration (ignore hours attached to the facilitator) ---
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*-?\s*(?:hours?|hrs?|h\b|heures?)", t):
        before = t[max(0, m.start() - 40):m.start()]
        hours = float(m.group(1).replace(",", "."))
        if re.search(SERVICE_PATTERNS["S4"], before) and not re.search(r"workshop|event|session|day", before):
            b.facilitator_hours = hours
            b.evidence["facilitator_hours"] = (before[-20:] + m.group(0)).strip()
            continue
        if b.duration_hours is None:
            b.duration_hours = hours
            b.evidence["duration_hours"] = m.group(0).strip()
    if b.duration_hours is None:
        m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(?:h|am|pm)?\s*(?:to|-|–|until|à)\s*(\d{1,2})(?::(\d{2}))?\s*(?:h\b|am|pm)?", t)
        if m and (m.group(2) or m.group(4) or "h" in m.group(0)):
            start = int(m.group(1)) + int(m.group(2) or 0) / 60
            end = int(m.group(3)) + int(m.group(4) or 0) / 60
            if 0 < end - start <= 12:
                b.duration_hours = round(end - start, 2)
                b.duration_text = m.group(0).strip()
                b.evidence["duration_hours"] = m.group(0).strip()
    if b.duration_hours is None:
        if re.search(r"half[- ]day|demi[- ]journ[ée]e|morning session|afternoon session", t):
            b.duration_hours, b.duration_text = 4, "half day"
            b.evidence["duration_hours"] = "half day"
        elif re.search(r"full[- ]day|whole day|all day|journ[ée]e compl[èe]te|toute la journ[ée]e", t):
            b.duration_hours, b.duration_text = 8, "full day"
            b.evidence["duration_hours"] = "full day"
    if b.facilitator_hours is None and re.search(r"facilitat\w*[^.]{0,30}(whole|entire|full|all)", t):
        b.facilitator_hours = b.duration_hours or 4
        b.evidence["facilitator_hours"] = "facilitator for the whole session"

    # --- budget (a per-head budget is converted to a total once the headcount is known) ---
    b.budget_eur, ev = _find_budget(t)
    if ev:
        b.evidence["budget_eur"] = ev
        after = t[t.find(ev) + len(ev):][:20] if ev in t else ""
        if re.search(r"^\s*(?:per|a|/)\s*(?:head|person|pers|personne|attendee|participant|pax)", after):
            if b.headcount:
                b.budget_eur = b.budget_eur * b.headcount
                b.evidence["budget_eur"] = f"{ev}{after.split(',')[0].split('.')[0]} x {b.headcount} people"
            else:
                b.budget_vague, b.budget_eur = f"{ev} per person", None
    if b.budget_eur is None:
        vm = re.search(VAGUE_BUDGET, t)
        if vm:
            b.budget_vague = vm.group(0)

    # --- services, required vs optional, with negation ---
    for sid, pat in SERVICE_PATTERNS.items():
        for c in clauses:
            if not re.search(pat, c):
                continue
            if re.search(NEGATION + rf"(?:{pat})", c):
                continue
            if sid == "S4" and re.search(r"second facilitator|two facilitators|2 facilitators", c):
                continue
            target = b.services_optional if re.search(OPTIONAL_MARKERS, c) else b.services_required
            if sid not in b.services_required and sid not in b.services_optional:
                target.append(sid)
    if not ({"S1", "S2"} & set(b.services_required + b.services_optional)) and re.search(FOOD_VAGUE, t):
        b.food_unspecified = True

    # --- accessibility ---
    if re.search(NO_ACCESS_NEED, t):
        b.wheelchair_access = False
    elif re.search(WHEELCHAIR, t):
        b.wheelchair_access = True

    # --- dietary / allergens ---
    for pat, label in DIETARY.items():
        if re.search(pat, t) and label not in b.dietary:
            b.dietary.append(label)
    if re.search(ALLERGY, t) and re.search(STRONG, t):
        b.allergen_guarantee_requested = True

    # --- unlisted items ---
    for pat, label in UNLISTED.items():
        for c in clauses:
            if re.search(pat, c) and not re.search(NEGATION + rf"(?:{pat})", c):
                strong = re.search(r"must|required|need|essential|have to|obligatoire|besoin", c)
                optional = re.search(OPTIONAL_MARKERS, c)
                lst = b.unlisted_required if strong and not optional else b.unlisted_requests
                if label not in b.unlisted_required + b.unlisted_requests:
                    lst.append(label)

    # --- safety net: a strongly-worded need we could not map to anything known ---
    known = "|".join(list(SERVICE_PATTERNS.values()) + list(UNLISTED) + [FOOD_VAGUE, WHEELCHAIR, ALLERGY,
                     r"wi-?fi|internet", r"\d+\s*(?:people|hours?|h\b)", r"budget|€|eur", "|".join(DIETARY)])
    for c in clauses:
        if re.search(r"non[- ]negotiable|absolutely need|must have|essential|mandatory|obligatoire|indispensable",
                     c) and not re.search(known, c):
            item = f"Unrecognised must-have: \"{c[:80]}\""
            if item not in b.unlisted_required:
                b.unlisted_required.append(item)

    if re.search(r"same room|all together|stay together|not (?:be )?split|splitting|no split|ensemble dans", t):
        b.keep_together = True

    # --- date / confirmation / discount ---
    for c in clauses:
        if re.search(CONFIRM, c):
            b.asks_confirmation = True
            continue  # "confirm it today" is about the reply, not the event date
        m = re.search(DATE, c)
        if m and b.date_text is None:
            b.date_text = m.group(0)
    if re.search(DISCOUNT, t):
        b.asks_discount = True
    return b
