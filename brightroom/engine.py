"""Deterministic proposal engine: venue choice, pricing, constraint checks, status and alternatives.

No LLM is involved here. Every number shown to the salesperson comes from this module.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .brief import Brief
from .catalogue import (DIETARY_AVAILABLE, FACILITATOR_HOURS, MAX_BOOKING_HOURS, MAX_CAPACITY,
                        SERVICES, VENUES, Venue)

NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
INFEASIBLE = "INFEASIBLE"
PROVISIONAL = "PROVISIONAL"
READY = "READY_FOR_REVIEW"

STATUS_LABEL = {
    NEEDS_CLARIFICATION: "Clarification needed — no proposal yet",
    INFEASIBLE: "Cannot meet the brief as stated — do not send the package as-is",
    PROVISIONAL: "Provisional proposal — check the labelled assumptions",
    READY: "Feasible draft — ready for salesperson review",
}


@dataclass
class LineItem:
    id: str
    name: str
    unit_price: int
    qty: int
    amount: int
    unit: str  # "booking" | "person"


@dataclass
class Package:
    headcount: int
    venue_id: str
    items: list[LineItem]
    label: str = ""

    @property
    def total(self) -> int:
        return sum(i.amount for i in self.items)


@dataclass
class Issue:
    code: str
    severity: str  # "blocker" | "warning" | "info"
    message: str


@dataclass
class Alternative:
    title: str
    packages: list[Package]
    changes: list[str]            # every difference from the client's brief
    must_have_changes: list[str]  # the subset that touches a confirmed requirement
    fits_budget: bool | None

    @property
    def total(self) -> int:
        return sum(p.total for p in self.packages)


@dataclass
class Result:
    status: str
    brief: Brief
    package: Package | None = None
    issues: list[Issue] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    alternatives: list[Alternative] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)       # transparent "why" notes (excluded venues etc.)
    budget_margin: float | None = None                   # budget - total (negative = overrun)
    omitted_optional: list[str] = field(default_factory=list)

    @property
    def blockers(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "blocker"]

    @property
    def allowed_amounts(self) -> set[int]:
        """Every euro figure the engine produced — used to audit LLM-written text."""
        nums: set[int] = set()
        pkgs = ([self.package] if self.package else []) + [p for a in self.alternatives for p in a.packages]
        for p in pkgs:
            nums.add(p.total)
            for i in p.items:
                nums.update({i.amount, i.unit_price})
        nums.update(a.total for a in self.alternatives)
        if self.brief.budget_eur is not None:
            nums.add(int(self.brief.budget_eur))
        if self.budget_margin is not None:
            nums.add(int(abs(self.budget_margin)))
        for a in self.alternatives:
            if self.brief.budget_eur is not None:
                nums.add(int(abs(self.brief.budget_eur - a.total)))
        # Catalogue list prices and every figure in engine-written text are also legitimate.
        nums.update(v.price for v in VENUES.values())
        nums.update(s.price for s in SERVICES.values())
        texts = self.assumptions + self.questions + self.notes + [i.message for i in self.issues] \
            + [c for a in self.alternatives for c in a.changes]
        for t in texts:
            nums.update(int(float(x.replace(" ", ""))) for x in re.findall(r"€(\d[\d ]*\d|\d)", t))
        return nums


# ---------------------------------------------------------------- pricing

def eligible_venues(headcount: int, wheelchair: bool | None) -> list[Venue]:
    vs = [v for v in VENUES.values() if headcount <= v.max_people and (v.wheelchair_accessible or not wheelchair)]
    return sorted(vs, key=lambda v: v.price)


def price_package(headcount: int, services: list[str], venue: Venue, label: str = "") -> Package:
    items = [LineItem(venue.id, f"{venue.name} (venue, {venue.hours} h)", venue.price, 1, venue.price, "booking")]
    for sid in sorted(set(services)):
        s = SERVICES[sid]
        qty = headcount if s.per_person else 1
        items.append(LineItem(s.id, s.name, s.price, qty, s.price * qty, "person" if s.per_person else "booking"))
    return Package(headcount, venue.id, items, label)


def cheapest_package(headcount: int, services: list[str], wheelchair: bool | None) -> Package | None:
    vs = eligible_venues(headcount, wheelchair)
    return price_package(headcount, services, vs[0]) if vs else None


def _split_sizes(n: int) -> list[int]:
    k = math.ceil(n / MAX_CAPACITY)
    base, extra = divmod(n, k)
    return [base + (1 if i < extra else 0) for i in range(k)]


def _svc_names(ids) -> str:
    return ", ".join(SERVICES[s].name.lower() for s in sorted(ids))


# ---------------------------------------------------------------- evaluation

def evaluate(brief: Brief) -> Result:
    r = Result(status=READY, brief=brief)
    b = brief

    # 1) Information we cannot proceed without -> ask, do not guess.
    if b.headcount is None:
        r.status = NEEDS_CLARIFICATION
        r.questions.append("How many people will attend? (Venue choice and every per-person price depend on it.)")
        if b.duration_hours is None:
            r.questions.append("How long should the workshop last? Our bookings are half-day blocks of 4 hours.")
        if b.budget_eur is None:
            r.questions.append("What total budget (EUR, all-inclusive) should the package stay within?")
        if not (b.services_required or b.services_optional) or b.food_unspecified:
            r.questions.append("Which services do you need: coffee break (€8/person), lunch (€18/person), "
                               "projector (€35), facilitator for 2 hours (€280)?")
        if b.wheelchair_access is None:
            r.questions.append("Does anyone need step-free / wheelchair access?")
        if b.date_text is None:
            r.questions.append("Which date(s) would you like? We will check availability before confirming.")
        _flag_promises(b, r)
        return r

    n = b.headcount
    services = list(dict.fromkeys(b.services_required))
    optional = [s for s in dict.fromkeys(b.services_optional) if s not in services]

    # 2) Labelled assumptions for non-blocking gaps.
    if b.headcount_approx:
        r.assumptions.append(f"Priced for {n} people (client wrote an approximate number); per-person items "
                             f"change with the final headcount.")
        r.questions.append(f"Can you confirm the final headcount (we priced {n})?")
    duration = b.duration_hours
    if duration is None:
        duration = MAX_BOOKING_HOURS
        r.assumptions.append("Duration not stated — assumed one standard 4-hour half-day booking.")
        r.questions.append("Is a 4-hour half-day session right for you?")
    elif b.duration_text:  # an exact reading ("half day", "9:00 to 13:00"), shown but not an assumption
        r.notes.append(f"'{b.duration_text}' read as {duration:g} hours.")
    if b.budget_eur is None:
        if b.budget_vague:
            r.assumptions.append(f"Budget described only as '{b.budget_vague}' — budget fit cannot be checked.")
        else:
            r.assumptions.append("No budget stated — budget fit not checked.")
        r.questions.append("What is the maximum total budget (EUR)?")
    if b.food_unspecified:
        services.append("S2")
        alt = cheapest_package(n, [s for s in services if s != "S2"] + ["S1"], b.wheelchair_access)
        r.assumptions.append("'Food' interpreted as lunch (S2). "
                             + (f"With a coffee break instead the total would be €{alt.total}." if alt else ""))
        r.questions.append("By 'food', do you mean lunch (€18/person), a coffee break (€8/person), or both?")

    # 3) Hard constraints from the catalogue.
    if n > MAX_CAPACITY:
        r.issues.append(Issue("CAPACITY", "blocker",
                              f"{n} people exceeds the largest venue (Loft, max {MAX_CAPACITY})."))
    if duration > MAX_BOOKING_HOURS:
        r.issues.append(Issue("DURATION", "blocker",
                              f"{duration:g} hours requested; venues are booked for {MAX_BOOKING_HOURS} hours and no "
                              f"longer-duration price exists."))
    if b.facilitator_hours and b.facilitator_hours > FACILITATOR_HOURS and ("S4" in services or "S4" in optional):
        r.issues.append(Issue("FACILITATOR_HOURS", "blocker",
                              f"Facilitation for {b.facilitator_hours:g} h requested; the catalogue offers one "
                              f"facilitator for {FACILITATOR_HOURS} h, added once."))
    food_in_pkg = bool({"S1", "S2"} & set(services + optional))
    if b.allergen_guarantee_requested:
        sev = "blocker" if food_in_pkg else "warning"
        r.issues.append(Issue("ALLERGEN", sev, "An allergen guarantee was requested; BrightRoom supplies no "
                                               "allergen guarantee for catering."))
    for d in b.dietary:
        if d in DIETARY_AVAILABLE:
            if "S2" not in services + optional:
                r.issues.append(Issue("DIETARY", "warning", f"{d.capitalize()} meals are available on request with "
                                                            f"lunch only; lunch is not in the package."))
            else:
                r.notes.append(f"{d.capitalize()} option to be requested with the lunch order.")
        elif not b.allergen_guarantee_requested:
            r.issues.append(Issue("DIETARY", "warning", f"'{d}' requirement: not a listed option and no allergen "
                                                        f"guarantee is supplied — do not promise it."))
    for item in b.unlisted_required:
        r.issues.append(Issue("UNLISTED_REQUIRED", "blocker", f"'{item}' is required but not in the catalogue."))
    for item in b.unlisted_requests:
        r.issues.append(Issue("UNLISTED", "warning", f"'{item}' is not in the catalogue — excluded, do not offer it."))
    _flag_promises(b, r)

    # 4) Build the requested package (unless the group cannot be hosted at all).
    structural = {i.code for i in r.blockers} & {"CAPACITY", "DURATION"}
    if not structural:
        venues = eligible_venues(n, b.wheelchair_access)
        pkg = price_package(n, services, venues[0])
        # Transparency: explain why a cheaper venue was not chosen.
        for v in VENUES.values():
            if v.price < venues[0].price:
                why = "not wheelchair accessible (stairs only)" if b.wheelchair_access and not v.wheelchair_accessible \
                    else f"holds at most {v.max_people} people"
                r.notes.append(f"{v.name} (€{v.price}) is cheaper but was excluded: {why}.")
        # Optional services are added only if they keep the package within budget.
        for sid in optional:
            trial = price_package(n, services + [sid], venues[0])
            if b.budget_eur is None or trial.total <= b.budget_eur:
                services.append(sid)
                pkg = trial
                r.notes.append(f"Optional item included: {SERVICES[sid].name}.")
            else:
                r.omitted_optional.append(sid)
                r.notes.append(f"Optional {SERVICES[sid].name} left out: total would be €{trial.total} "
                               f"(over budget by €{trial.total - b.budget_eur:g}).")
        r.package = pkg
        if b.wheelchair_access is None and not VENUES[pkg.venue_id].wheelchair_accessible:
            r.assumptions.append(f"Accessibility not mentioned — {VENUES[pkg.venue_id].name} is stairs-only.")
            r.questions.append("Does anyone need step-free access? The proposed Studio is reachable by stairs only "
                               "(the accessible Loft costs €180 more).")
        if b.budget_eur is not None:
            r.budget_margin = b.budget_eur - pkg.total
            if r.budget_margin < 0:
                r.issues.append(Issue("BUDGET", "blocker",
                                      f"Package total €{pkg.total} exceeds the budget of €{b.budget_eur:g} "
                                      f"by €{-r.budget_margin:g}."))

    # 5) Status + alternatives.
    if r.blockers:
        r.status = INFEASIBLE
        r.alternatives = generate_alternatives(b, services, optional, duration)
    elif r.questions or r.assumptions or any(i.code in ("UNLISTED", "DIETARY") for i in r.issues):
        r.status = PROVISIONAL
    else:
        r.status = READY
    return r


def _flag_promises(b: Brief, r: Result) -> None:
    if b.asks_confirmation:
        r.issues.append(Issue("NO_CONFIRMATION", "warning",
                              "Client asks for confirmation/booking — availability is unconfirmed; this is a draft "
                              "and nothing can be booked or confirmed yet."))
    if b.asks_discount:
        r.issues.append(Issue("NO_DISCOUNT", "warning",
                              "Client asks for a discount/'best offer' — no discounts exist; offer the cheapest "
                              "package that meets the brief at list prices."))
    if b.date_text:
        r.issues.append(Issue("DATE", "info", f"Requested timing '{b.date_text}' — availability must be checked "
                                              f"separately; do not promise the date."))


# ---------------------------------------------------------------- alternatives

BASE = "Requested package, adjusted"


def generate_alternatives(b: Brief, services: list[str], optional: list[str], duration: float) -> list[Alternative]:
    """Candidate modifications of the brief, each re-priced by the same engine with every change listed."""
    n = b.headcount
    budget = b.budget_eur
    wc = b.wheelchair_access

    # Structural fixes (always required for any alternative).
    base_changes, base_must = [], []
    svc = list(services)
    if duration > MAX_BOOKING_HOURS:
        c = f"Shorten from {duration:g} h to {MAX_BOOKING_HOURS} h (no longer booking exists)"
        base_changes.append(c)
        base_must.append(c)
    if b.facilitator_hours and b.facilitator_hours > FACILITATOR_HOURS and "S4" in svc:
        c = f"Facilitation covers {FACILITATOR_HOURS} h, not {b.facilitator_hours:g} h"
        base_changes.append(c)
        base_must.append(c)
    if b.allergen_guarantee_requested and {"S1", "S2"} & set(svc):
        c = "Catering served without an allergen guarantee — you would need to accept this explicitly"
        base_changes.append(c)
        base_must.append(c)
    for item in b.unlisted_required:
        c = f"'{item}' not included (not in catalogue)"
        base_changes.append(c)
        base_must.append(c)

    # Capacity variants: reduce to max, or split into separate bookings.
    shapes: list[tuple[str, list[int], list[str], list[str]]] = []
    if n > MAX_CAPACITY:
        c = f"Reduce the group from {n} to {MAX_CAPACITY} people"
        shapes.append(("Single booking at maximum capacity", [MAX_CAPACITY], [c], [c]))
        if not b.keep_together:  # client said the group must stay in one room -> never offer a split
            sizes = _split_sizes(n)
            c2 = (f"Split into {len(sizes)} separate bookings ({' + '.join(map(str, sizes))} people) — the group "
                  f"is not together; each booking needs its own availability check")
            shapes.append((f"{len(sizes)} separate bookings", sizes, [c2], [c2]))
    else:
        shapes.append((BASE, [n], [], []))

    alts: list[Alternative] = []
    for title, sizes, ch, must in shapes:
        pkgs = [cheapest_package(s, svc, wc) for s in sizes]
        if any(p is None for p in pkgs):
            continue
        changes, must_ch = base_changes + ch, base_must + must
        total = sum(p.total for p in pkgs)
        fits = None if budget is None else total <= budget
        if fits is not False:
            if changes:
                alts.append(Alternative(title, pkgs, changes, must_ch, fits))
            continue
        # Over budget: budget-side options for this shape.
        over = total - budget
        alts.append(Alternative("Keep everything, raise the budget" if title == BASE else
                                f"{title} — raise the budget", pkgs,
                                changes + [f"Budget raised from €{budget:g} to €{total} (+€{over:g}) — client "
                                           f"must approve"],
                                must_ch + ["Exceeds the stated budget"], False))
        if len(sizes) == 1:
            s_n = sizes[0]
            # Drop each required service, one at a time (explicitly a must-have change).
            for sid in svc:
                rest = [x for x in svc if x != sid]
                p = cheapest_package(s_n, rest, wc)
                if p and p.total <= budget:
                    c = f"Remove {SERVICES[sid].name.lower()} (a requested service)"
                    alts.append(Alternative(f"Without {SERVICES[sid].name.lower()}" if title == BASE else
                                            f"{title}, without {SERVICES[sid].name.lower()}", [p],
                                            changes + [c], must_ch + [c], True))
            # Reduce headcount (venue re-selected) while keeping all services.
            best = None
            for m in range(s_n - 1, 0, -1):
                p = cheapest_package(m, svc, wc)
                if p and p.total <= budget:
                    best = p
                    break
            if best:
                c = f"Reduce the group from {s_n} to {best.headcount} people"
                alts.append(Alternative(f"{best.headcount} people, all requested services", [best],
                                        changes + [c], must_ch + [c], True))

    # Allergen guarantee cannot be met: the honest alternative is no catering at all.
    if b.allergen_guarantee_requested and {"S1", "S2"} & set(svc) and n <= MAX_CAPACITY:
        rest = [x for x in svc if x not in ("S1", "S2")]
        p = cheapest_package(n, rest, wc)
        if p:
            c = f"Remove catering ({_svc_names({'S1', 'S2'} & set(svc))}) — no allergen guarantee can be given"
            ch = [x for x in base_changes if not x.startswith("Catering served without")] + [c]
            mu = [x for x in base_must if not x.startswith("Catering served without")] + [c]
            alts.append(Alternative("Package without catering", [p], ch, mu,
                                    None if budget is None else p.total <= budget))

    # Never let an alternative quietly move the group to the stairs-only venue.
    if wc is None:
        for a in alts:
            if any(not VENUES[p.venue_id].wheelchair_accessible for p in a.packages):
                a.changes.append("Uses the Studio (stairs only) — check nobody needs step-free access")

    # Rank: fits budget first, then fewest must-have changes, then closest to the
    # requested package (highest total = least removed).
    alts.sort(key=lambda a: (a.fits_budget is False, len(a.must_have_changes), -a.total))
    seen, out = set(), []
    for a in alts:
        key = (tuple((p.headcount, p.venue_id, p.total) for p in a.packages), tuple(a.changes))
        if key not in seen:
            seen.add(key)
            out.append(a)
    return out[:5]
