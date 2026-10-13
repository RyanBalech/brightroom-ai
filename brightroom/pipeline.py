"""End-to-end workflow: enquiry -> brief -> deterministic evaluation -> reviewed draft."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import llm
from .brief import Brief
from .draft import audit_text, facts_for_llm, render_client_draft, render_review, template_cover_note
from .engine import PROVISIONAL, READY, Result, evaluate
from .extract_rules import extract_rules


@dataclass
class Output:
    enquiry: str
    result: Result
    review_md: str
    client_md: str
    cover_source: str                     # "llm" | "template" | "template (llm text rejected)"
    audit_violations: list[str] = field(default_factory=list)
    llm_errors: list[str] = field(default_factory=list)
    seconds: float = 0.0


def _cross_check(llm_b: Brief, rules_b: Brief) -> list[str]:
    diffs = []
    for f in ("headcount", "duration_hours", "budget_eur", "wheelchair_access"):
        a, b = getattr(llm_b, f), getattr(rules_b, f)
        if a is not None and b is not None and float(a) != float(b):
            diffs.append(f"LLM read {f}={a:g} but the rule check read {b:g} — confirm with the client."
                         if not isinstance(a, bool) else f"LLM and rule check disagree on {f} — confirm.")
    a = set(llm_b.services_required + llm_b.services_optional)
    b = set(rules_b.services_required + rules_b.services_optional)
    if a != b and a and b:
        diffs.append(f"Services differ: LLM {sorted(a)} vs rule check {sorted(b)} — confirm.")
    return diffs


def extract(enquiry: str, use_llm: bool | None = None, errors: list | None = None) -> Brief:
    rules_b = extract_rules(enquiry)
    if use_llm is None:
        use_llm = llm.llm_available()
    if not use_llm:
        return rules_b
    try:
        llm_b = llm.extract_llm(enquiry)
    except Exception as e:  # network, auth, refusal, schema: never block the salesperson
        if errors is not None:
            errors.append(f"LLM extraction failed ({type(e).__name__}: {e}); used rule-based extraction.")
        return rules_b
    llm_b.extractor = "llm+rules"
    llm_b.extraction_warnings += _cross_check(llm_b, rules_b)
    return llm_b


def run(enquiry: str, use_llm: bool | None = None) -> Output:
    t0 = time.perf_counter()
    errors: list[str] = []
    if use_llm is None:
        use_llm = llm.llm_available()
    brief = extract(enquiry, use_llm, errors)
    result = evaluate(brief)
    if brief.extraction_warnings:
        if result.status == READY:
            result.status = PROVISIONAL
        result.questions.append("Please confirm the details flagged by the extraction check.")

    cover, source, violations = template_cover_note(result), "template", []
    if use_llm:
        try:
            text = llm.cover_note_llm(facts_for_llm(result, enquiry))
            violations = audit_text(text, result)
            if violations:
                source = "template (LLM text rejected by guardrail)"
            else:
                cover, source = text, "llm"
        except Exception as e:
            errors.append(f"LLM cover note failed ({type(e).__name__}); used template.")
    return Output(enquiry, result, render_review(result), render_client_draft(result, cover), source,
                  violations, errors, time.perf_counter() - t0)
