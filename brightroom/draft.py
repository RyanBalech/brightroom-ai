"""Render the salesperson review sheet and the client-facing draft.

Every table and figure is produced by code from the engine Result. The (optional) LLM only
writes the covering paragraph, which is audited by `audit_text` before use.
"""
from __future__ import annotations

import re

from .brief import Brief
from .catalogue import SERVICES, VENUES
from .engine import (INFEASIBLE, NEEDS_CLARIFICATION, PROVISIONAL, READY, STATUS_LABEL, Package,
                     Result)

STATUS_ICON = {READY: "🟢", PROVISIONAL: "🟡", INFEASIBLE: "🔴", NEEDS_CLARIFICATION: "🔵"}

# Affirmative promises the draft must never make.
BANNED = [
    (r"\b(?:is|are|has been|have been|we have|we've)\s+(?:now\s+)?(?:confirmed|booked|reserved)\b", "confirms/books"),
    (r"\bwe (?:confirm|will confirm|have booked|have reserved|can confirm)\b", "confirms/books"),
    (r"\b(?:reserved|booked) for you\b", "confirms/books"),
    (r"(?<!no )(?<!not )(?<!cannot )(?<!can't )(?<!can not )\bguarantee(?:d|s)?\b(?! is supplied)", "guarantee"),
    (r"\bdiscount(?:ed)?\b(?! is| are)|\b\d+\s*% off\b|\bspecial (?:price|rate)\b", "discount"),
    (r"\b(?:is|are) available on\b|\bavailability is confirmed\b|\bwe have availability\b", "availability promise"),
]


def audit_text(text: str, result: Result) -> list[str]:
    """Return guardrail violations in a piece of (LLM-written) client text."""
    problems = []
    low = text.lower()
    for pat, label in BANNED:
        m = re.search(pat, low)
        if m and not re.search(r"\b(?:no|not|cannot|can't|unable)\b[^.]{0,40}$", low[:m.start()]):
            problems.append(f"{label}: '{m.group(0)}'")
    allowed = result.allowed_amounts
    num = r"(\d{1,3}(?:[ ,\u202f\xa0]\d{3})+|\d+)(?:\.\d+)?"
    for m in re.finditer(rf"(?:€|eur\s?)\s*{num}|{num}\s*(?:€|eur\b|euros?\b)", low):
        raw = re.sub(r"[ ,\u202f\xa0]", "", m.group(1) or m.group(2))
        try:
            val = int(float(raw))
        except ValueError:
            continue
        if val not in allowed:
            problems.append(f"amount €{raw} is not produced by the pricing engine")
    known = {s.name.lower() for s in SERVICES.values()} | {v.name.lower() for v in VENUES.values()}
    for item in result.brief.unlisted_requests + result.brief.unlisted_required:
        if item.lower() in low and item.lower() not in known and not re.search(
                rf"(?:not|no|cannot|can't|unable)[^.]{{0,60}}{re.escape(item.lower())}|"
                rf"{re.escape(item.lower())}[^.]{{0,60}}(?:not (?:in|part|offered|available|included))", low):
            problems.append(f"mentions unlisted item '{item}' without saying it is unavailable")
    return problems


# ------------------------------------------------------------------ helpers

def eur(x: float) -> str:
    return f"€{x:,.0f}".replace(",", " ")


def package_table(p: Package) -> str:
    rows = ["| Item | Unit price | Qty | Amount |", "|---|---:|---:|---:|"]
    for i in p.items:
        unit = "/person" if i.unit == "person" else ""
        rows.append(f"| {i.id} · {i.name} | {eur(i.unit_price)}{unit} | {i.qty} | {eur(i.amount)} |")
    rows.append(f"| **Total ({p.headcount} people)** | | | **{eur(p.total)}** |")
    return "\n".join(rows)


def brief_table(b: Brief) -> tuple[list[str], list[str], list[str]]:
    """Confirmed requirements / optional preferences / missing information."""
    confirmed, optional, missing = [], [], []
    if b.headcount is not None:
        confirmed.append(f"Headcount: {'about ' if b.headcount_approx else ''}{b.headcount}")
    else:
        missing.append("Headcount")
    if b.duration_hours is not None:
        confirmed.append(f"Duration: {b.duration_hours:g} h" + (f" ('{b.duration_text}')" if b.duration_text else ""))
    else:
        missing.append("Duration")
    if b.budget_eur is not None:
        confirmed.append(f"Budget: {eur(b.budget_eur)}")
    else:
        missing.append("Budget" + (f" (only '{b.budget_vague}')" if b.budget_vague else ""))
    for s in b.services_required:
        confirmed.append(f"Service (must-have): {SERVICES[s].name}")
    for s in b.services_optional:
        optional.append(f"Service (nice-to-have): {SERVICES[s].name}")
    if b.food_unspecified:
        missing.append("Type of food (coffee break or lunch?)")
    if not (b.services_required or b.services_optional or b.food_unspecified):
        missing.append("Services (none mentioned)")
    if b.wheelchair_access is True:
        confirmed.append("Accessibility: wheelchair / step-free access needed")
    elif b.wheelchair_access is False:
        confirmed.append("Accessibility: no special needs")
    else:
        missing.append("Accessibility needs (not mentioned)")
    if b.facilitator_hours:
        confirmed.append(f"Facilitation length: {b.facilitator_hours:g} h")
    for d in b.dietary:
        confirmed.append(f"Dietary: {d}")
    if b.allergen_guarantee_requested:
        confirmed.append("Allergen guarantee requested")
    for u in b.unlisted_required:
        confirmed.append(f"Not in catalogue (must-have): {u}")
    for u in b.unlisted_requests:
        optional.append(f"Not in catalogue: {u}")
    if b.date_text:
        optional.append(f"Timing: {b.date_text} (availability unconfirmed)")
    else:
        missing.append("Date")
    if b.asks_confirmation:
        optional.append("Asks for confirmation / booking")
    if b.asks_discount:
        optional.append("Asks for a discount / best offer")
    return confirmed, optional, missing


def facts_for_llm(result: Result, enquiry: str) -> dict:
    b = result.brief
    return {
        "client_enquiry": enquiry,
        "status": result.status,
        "requirements_that_cannot_be_met": [i.message for i in result.blockers],
        "things_we_cannot_promise": [i.message for i in result.issues if i.severity != "blocker"],
        "assumptions": result.assumptions,
        "open_questions_count": len(result.questions),
        "proposed_venue": VENUES[result.package.venue_id].name if result.package else None,
        "proposed_services": [i.name for i in result.package.items[1:]] if result.package else [],
        "headcount": b.headcount,
        "number_of_alternatives": len(result.alternatives),
    }


def template_cover_note(result: Result) -> str:
    b, s = result.brief, result.status
    if s == NEEDS_CLARIFICATION:
        return ("Thank you for your enquiry. To prepare an accurate proposal from our catalogue we need a few "
                "details first — please see the questions below. As soon as we have them we will send an "
                "itemised quote.")
    if s == INFEASIBLE:
        reasons = "; ".join(i.message[0].lower() + i.message[1:].rstrip(".") for i in result.blockers) + "."
        return ("Thank you for your enquiry. We have checked it carefully against our catalogue and, as stated, "
                f"we cannot meet every requirement: {reasons} Rather than change your request silently, we list "
                "realistic alternatives below, each with its trade-offs, so you can choose what matters most.")
    venue = VENUES[result.package.venue_id].name
    txt = (f"Thank you for your enquiry. Based on our catalogue, we suggest the {venue} for your group of "
           f"{b.headcount}, with the itemised package below.")
    if s == PROVISIONAL:
        txt += " Some points were not stated in your message, so we noted our assumptions and a few questions below."
    return txt + " This is a draft quote; the date is subject to an availability check."


# ------------------------------------------------------------------ rendering

def render_client_draft(result: Result, cover: str) -> str:
    out = ["**DRAFT — for salesperson approval. Not sent. Nothing is booked.**", "", cover, ""]
    if result.package and result.status != INFEASIBLE:
        out += ["#### Proposed package", package_table(result.package), ""]
        if result.brief.budget_eur is not None:
            out.append(f"Your budget: {eur(result.brief.budget_eur)} · within budget by "
                       f"{eur(result.budget_margin)}.\n")
    if result.status == INFEASIBLE:
        # Show the as-stated package only when it adds information (the budget overrun); otherwise
        # it would duplicate the first alternative.
        if result.package and any(i.code == "BUDGET" for i in result.blockers):
            out += ["#### Package for the request as stated (over budget)", package_table(result.package), ""]
        if result.alternatives:
            out.append("#### Alternatives — each one changes your request")
            for k, a in enumerate(result.alternatives, 1):
                fit = "" if a.fits_budget is None else (" · within budget" if a.fits_budget else " · **above budget**")
                out.append(f"**Option {k}: {a.title} — {eur(a.total)}{fit}**")
                out.append("Trade-offs: " + "; ".join(a.changes) + ".")
                for p in a.packages:
                    out += ["", package_table(p)]
                out.append("")
        else:
            out.append("No alternative within the catalogue meets the remaining requirements.\n")
    if result.assumptions and result.status != NEEDS_CLARIFICATION:
        out += ["#### Assumptions (please correct us)"] + [f"- {a}" for a in result.assumptions] + [""]
    if result.questions:
        out += ["#### Questions"] + [f"{k}. {q}" for k, q in enumerate(result.questions, 1)] + [""]
    notes = ["Prices are total amounts in euros from our catalogue; no taxes or other fees are added.",
             "Dates and venue availability are not confirmed; this is not a booking."]
    pkgs = ([result.package] if result.package else []) + [p for a in result.alternatives for p in a.packages]
    if any(i.id == "S2" for p in pkgs for i in p.items):
        notes.append("Lunch: vegetarian/vegan on request; no allergen guarantee is supplied.")
    for i in result.issues:
        if i.code in ("UNLISTED", "UNLISTED_REQUIRED"):
            item = re.search(r"'(.+?)'", i.message).group(1)
            notes.append(f"{item} is not part of our catalogue and is not included.")
        if i.code == "NO_CONFIRMATION":
            notes.append("We cannot confirm or book anything yet: availability must be checked first, then the "
                         "salesperson will confirm in writing.")
        if i.code == "NO_DISCOUNT":
            notes.append("Our catalogue prices are fixed; the package above is the lowest-cost option that meets "
                         "the stated needs.")
    out += ["#### Notes"] + [f"- {n}" for n in dict.fromkeys(notes)]
    return "\n".join(out)


def render_review(result: Result) -> str:
    """Internal sheet: what the salesperson must check before sending."""
    out = [f"### {STATUS_ICON[result.status]} {STATUS_LABEL[result.status]}"]
    if result.package and result.brief.budget_eur is not None:
        m = result.budget_margin
        out.append(f"Total {eur(result.package.total)} vs budget {eur(result.brief.budget_eur)} → "
                   + (f"**{eur(m)} under budget**" if m >= 0 else f"**{eur(-m)} OVER budget**"))
    sev_icon = {"blocker": "⛔", "warning": "⚠️", "info": "ℹ️"}
    if result.issues:
        out += [""] + [f"- {sev_icon[i.severity]} **{i.code}** — {i.message}" for i in result.issues]
    for w in result.brief.extraction_warnings:
        out.append(f"- 🔍 Extraction check — {w}")
    if result.notes:
        out += [""] + [f"- {n}" for n in result.notes]
    return "\n".join(out)
