"""Unit tests for the deterministic parts (pytest)."""
import json
import pathlib

import pytest

from brightroom.brief import Brief
from brightroom.draft import audit_text
from brightroom.engine import INFEASIBLE, NEEDS_CLARIFICATION, READY, evaluate
from brightroom.extract_rules import extract_rules
from brightroom.pipeline import run
from eval.run_eval import check

CASES = json.loads((pathlib.Path(__file__).parents[1] / "eval" / "cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_cases_offline(case):
    ok, fails = check(case, run(case["enquiry"], use_llm=False))
    assert ok, fails


def test_pricing_q2_exact():
    r = evaluate(Brief(headcount=20, duration_hours=4, budget_eur=850, services_required=["S1", "S2"],
                       wheelchair_access=False))
    assert [i.amount for i in r.package.items] == [420, 160, 360]
    assert r.package.total == 940 and r.budget_margin == -90 and r.status == INFEASIBLE


def test_wheelchair_never_uses_studio():
    r = evaluate(Brief(headcount=4, duration_hours=4, budget_eur=10_000, wheelchair_access=True))
    assert r.package.venue_id == "V2"


def test_flat_items_added_once():
    r = evaluate(Brief(headcount=20, duration_hours=4, services_required=["S3", "S4", "S3"], wheelchair_access=False,
                       budget_eur=5000))
    assert sum(1 for i in r.package.items if i.id == "S3") == 1
    assert r.package.total == 420 + 35 + 280


def test_alternatives_never_silently_drop_must_haves():
    r = evaluate(Brief(headcount=20, duration_hours=4, budget_eur=500, services_required=["S1", "S2"]))
    for a in r.alternatives:
        kept = {i.id for p in a.packages for i in p.items}
        for s in ("S1", "S2"):
            if s not in kept:
                assert any(("coffee" if s == "S1" else "lunch") in c.lower() for c in a.must_have_changes)


def test_missing_headcount_asks_and_does_not_price():
    r = evaluate(extract_rules("Can we do a workshop with lunch next week? Budget 900 EUR."))
    assert r.status == NEEDS_CLARIFICATION and r.package is None and r.questions


def test_budget_equal_is_feasible():
    r = evaluate(Brief(headcount=10, duration_hours=4, budget_eur=320, services_required=["S1"],
                       wheelchair_access=False))
    assert r.status == READY and r.budget_margin == 0


@pytest.mark.parametrize("text,expect", [
    ("20 people, 4 hours, budget €1,500", (20, 4, 1500)),
    ("nous sommes 12 personnes, 3 heures, budget 1 200 €", (12, 3, 1200)),
    ("Team of 9, half-day, max 500 euros", (9, 4, 500)),
    ("for about 15 people, budget: 700", (15, None, 700)),
])
def test_rule_extraction_numbers(text, expect):
    b = extract_rules(text)
    assert (b.headcount, b.duration_hours, b.budget_eur) == expect


def test_guardrail_catches_invented_numbers_and_promises():
    r = evaluate(Brief(headcount=10, duration_hours=4, budget_eur=350, services_required=["S1"],
                       wheelchair_access=False))
    bad = "Great news: the Studio is confirmed for you at €299, and we can offer a 10% discount."
    problems = audit_text(bad, r)
    assert any("299" in p for p in problems)
    assert any("discount" in p for p in problems)
    assert any("confirm" in p for p in problems)
    good = "Thank you! The itemised package below is a draft; availability is not confirmed and no discount applies."
    assert audit_text(good, r) == []
