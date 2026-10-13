"""Run every test case through the prototype and check it against the expected behaviour.

    python -m eval.run_eval            # uses Claude if credentials are set, else rules only
    python -m eval.run_eval --offline  # rules only (deterministic, free)

Writes eval/results_prototype.md and eval/results_prototype.json.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time

from brightroom.catalogue import SERVICES, VENUES
from brightroom.draft import audit_text
from brightroom.pipeline import run

HERE = pathlib.Path(__file__).parent


def independent_total(pkg) -> int:
    """Re-price a package straight from the catalogue (catches arithmetic bugs in the engine)."""
    total = 0
    for i in pkg.items:
        if i.id in VENUES:
            total += VENUES[i.id].price
        else:
            s = SERVICES[i.id]
            total += s.price * (pkg.headcount if s.per_person else 1)
    return total


def check(case: dict, out) -> tuple[bool, list[str]]:
    exp, r = case["expected"], out.result
    fails = []
    if r.status not in exp["status"]:
        fails.append(f"status {r.status} not in {exp['status']}")
    if "total" in exp:
        got = r.package.total if r.package else None
        if got != exp["total"]:
            fails.append(f"total {got} != {exp['total']}")
    if exp.get("venue") and (not r.package or r.package.venue_id != exp["venue"]):
        fails.append(f"venue {r.package.venue_id if r.package else None} != {exp['venue']}")
    if "within_budget" in exp and r.budget_margin is not None and (r.budget_margin >= 0) != exp["within_budget"]:
        fails.append(f"budget fit wrong (margin {r.budget_margin})")
    codes = {i.code for i in r.issues}
    for c in exp.get("codes", []):
        if c not in codes:
            fails.append(f"missing flag {c}")
    alt_totals = {a.total for a in r.alternatives}
    for t in exp.get("alt_totals", []):
        if t not in alt_totals:
            fails.append(f"alternative €{t} missing (got {sorted(alt_totals)})")
    pkgs = ([r.package] if r.package else []) + [p for a in r.alternatives for p in a.packages]
    if exp.get("forbid_venue") and any(p.venue_id == exp["forbid_venue"] for p in pkgs):
        fails.append(f"forbidden venue {exp['forbid_venue']} proposed")
    # Universal guardrails
    for p in pkgs:
        if p.total != independent_total(p):
            fails.append("arithmetic mismatch")
        v = VENUES[p.venue_id]
        if p.headcount > v.max_people:
            fails.append("venue capacity exceeded")
        if r.brief.wheelchair_access and not v.wheelchair_accessible:
            fails.append("inaccessible venue proposed")
    for a in r.alternatives:
        if not a.changes:
            fails.append(f"alternative '{a.title}' has no stated trade-off")
        dropped = [s for s in r.brief.services_required
                   if all(s not in {i.id for i in p.items} for p in a.packages)]
        for s in dropped:
            if not any(SERVICES[s].name.lower() in c.lower() for c in a.must_have_changes):
                fails.append(f"alternative silently drops must-have {s}")
    if not out.client_md.startswith("**DRAFT"):
        fails.append("draft label missing")
    if r.status == "NEEDS_CLARIFICATION" and (r.package or not r.questions):
        fails.append("clarification case priced or asked nothing")
    fails += [f"guardrail: {v}" for v in audit_text(out.client_md.split("#### Notes")[0], r)
              if "not produced by the pricing engine" in v]
    return not fails, fails


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--cases", default="cases.json", help="cases file in eval/ (e.g. heldout_cases.json)")
    a = ap.parse_args()
    cases = json.loads((HERE / a.cases).read_text(encoding="utf-8"))
    tag = {"cases.json": "prototype", "heldout_cases.json": "heldout"}.get(a.cases, a.cases.removesuffix("_cases.json"))
    rows, dump = [], []
    t0 = time.perf_counter()
    for c in cases:
        out = run(c["enquiry"], use_llm=False if a.offline else None)
        ok, fails = check(c, out)
        r = out.result
        got = f"{r.status}; total " + (f"€{r.package.total}" if r.package else "—")
        if r.alternatives:
            got += "; alts " + ", ".join(f"€{x.total}" for x in r.alternatives)
        rows.append(f"| {c['id']} | {c['type']} | {c['expected']['behaviour']} | {got} | "
                    f"{'PASS' if ok else 'FAIL: ' + '; '.join(fails)} |")
        dump.append({"id": c["id"], "pass": ok, "fails": fails, "status": r.status,
                     "total": r.package.total if r.package else None, "extractor": r.brief.extractor,
                     "cover_source": out.cover_source, "seconds": round(out.seconds, 3),
                     "llm_errors": out.llm_errors, "review_md": out.review_md, "client_md": out.client_md})
        print(f"{c['id']}: {'PASS' if ok else 'FAIL'} {'' if ok else fails}")
    passed = sum(d["pass"] for d in dump)
    mode = dump[0]["extractor"] if dump else "?"
    md = [f"# {tag.capitalize()} results — {passed}/{len(dump)} pass (extractor: {mode}, "
          f"total runtime {time.perf_counter() - t0:.2f}s)", "",
          "| ID | Type | Expected behaviour | Prototype result | Judgement |", "|---|---|---|---|---|", *rows]
    (HERE / f"results_{tag}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (HERE / f"results_{tag}.json").write_text(
        json.dumps(dump, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n{passed}/{len(dump)} passed")


if __name__ == "__main__":
    main()
