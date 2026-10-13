"""LLM path with a fake client: checks grounding, cross-check and guardrail wiring (no API calls)."""
import json
from types import SimpleNamespace

from brightroom import llm, pipeline

ENQ = "20 people, 4 hours, coffee and lunch are required. Total budget €850."


def fake_extraction(**over):
    d = {"headcount": 20, "headcount_approx": False, "headcount_quote": "20 people",
         "duration_hours": 4, "duration_quote": "4 hours", "budget_eur": 850, "budget_quote": "budget €850",
         "budget_vague": None, "budget_per_person_eur": None, "keep_together": False,
         "services": [{"id": "S1", "priority": "required", "quote": "coffee"},
                      {"id": "S2", "priority": "required", "quote": "lunch are required"}],
         "food_unspecified": False, "facilitator_hours": None, "wheelchair_access": None, "dietary": [],
         "allergen_guarantee_requested": False, "unlisted": [], "date_text": None,
         "asks_confirmation": False, "asks_discount": False}
    d.update(over)
    return d


class FakeClient:
    def __init__(self, extraction, cover):
        self.extraction, self.cover = extraction, cover
        self.messages = self

    def create(self, **kw):
        text = json.dumps(self.extraction) if "format" in kw.get("output_config", {}) else self.cover
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def _run(monkeypatch, extraction, cover):
    monkeypatch.setattr(llm, "_client", lambda: FakeClient(extraction, cover))
    return pipeline.run(ENQ, use_llm=True)


def test_llm_happy_path(monkeypatch):
    out = _run(monkeypatch, fake_extraction(), "Thank you — we cannot fit everything in your budget; options below.")
    assert out.result.brief.extractor == "llm+rules"
    assert out.result.package.total == 940
    assert out.cover_source == "llm"


def test_ungrounded_number_is_discarded(monkeypatch):
    out = _run(monkeypatch, fake_extraction(headcount=25, headcount_quote="25 people"), "ok")
    assert out.result.brief.headcount is None          # quote not in enquiry -> dropped -> ask
    assert out.result.status == "NEEDS_CLARIFICATION"


def test_guardrail_rejects_bad_cover(monkeypatch):
    out = _run(monkeypatch, fake_extraction(), "Your Loft is booked for you at €799 with a 10% discount!")
    assert out.cover_source.startswith("template")
    assert out.audit_violations


def test_api_failure_falls_back_to_rules(monkeypatch):
    def boom():
        raise RuntimeError("no network")
    monkeypatch.setattr(llm, "_client", boom)
    out = pipeline.run(ENQ, use_llm=True)
    assert out.result.brief.extractor == "rules" and out.result.package.total == 940
    assert out.llm_errors


def test_grounding_accepts_number_words_and_time_ranges():
    enq = "A strategy workshop for twenty-four colleagues, 9:00 to 13:00, budget 1.2k EUR."
    assert llm._grounded("twenty-four colleagues", enq, 24, "headcount")
    assert llm._grounded("9:00 to 13:00", enq, 4, "duration_hours")
    assert llm._grounded("budget 1.2k EUR", enq, 1200, "budget_eur")
    assert not llm._grounded("twenty colleagues", enq, 20, "headcount")      # not in the enquiry
    assert not llm._grounded("twenty-four colleagues", enq, 25, "headcount")  # wrong number
