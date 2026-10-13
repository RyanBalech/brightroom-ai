"""Plain-dict views of engine results (shared by the MCP server and exports)."""
from __future__ import annotations

from .catalogue import SERVICES, VENUES
from .draft import brief_table
from .engine import STATUS_LABEL, Package, Result


def package_to_dict(p: Package) -> dict:
    return {
        "headcount": p.headcount,
        "venue": f"{p.venue_id} {VENUES[p.venue_id].name}",
        "items": [{"id": i.id, "name": i.name, "unit_price_eur": i.unit_price, "qty": i.qty,
                   "amount_eur": i.amount} for i in p.items],
        "total_eur": p.total,
    }


def result_to_dict(r: Result) -> dict:
    confirmed, optional, missing = brief_table(r.brief)
    return {
        "status": r.status,
        "status_label": STATUS_LABEL[r.status],
        "brief": {"confirmed": confirmed, "optional_or_other": optional, "missing": missing,
                  "evidence_quotes": r.brief.evidence, "extractor": r.brief.extractor},
        "package": package_to_dict(r.package) if r.package else None,
        "budget_eur": r.brief.budget_eur,
        "budget_margin_eur": r.budget_margin,
        "blockers": [f"{i.code}: {i.message}" for i in r.blockers],
        "warnings": [f"{i.code}: {i.message}" for i in r.issues if i.severity != "blocker"],
        "assumptions": r.assumptions,
        "questions_for_client": r.questions,
        "notes": r.notes,
        "alternatives": [{"title": a.title, "total_eur": a.total, "fits_budget": a.fits_budget,
                          "trade_offs": a.changes, "changes_a_must_have": bool(a.must_have_changes),
                          "packages": [package_to_dict(p) for p in a.packages]} for a in r.alternatives],
    }


def catalogue_dict() -> dict:
    from .catalogue import RULES_TEXT
    return {
        "venues": [{"id": v.id, "name": v.name, "price_eur": v.price, "hours": v.hours, "max_people": v.max_people,
                    "wheelchair_accessible": v.wheelchair_accessible, "conditions": v.notes}
                   for v in VENUES.values()],
        "services": [{"id": s.id, "name": s.name, "price_eur": s.price,
                      "pricing": "per person" if s.per_person else "flat, once per booking", "conditions": s.notes}
                     for s in SERVICES.values()],
        "rules": RULES_TEXT,
    }
