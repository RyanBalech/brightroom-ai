# Baseline results — single prompt (graded by rubric)

**Baseline**: the exact prompt in `eval/baseline.py` (catalogue + rules + enquiry, "write a proposal with itemised
prices and a total"), one sample per case. Raw outputs: `eval/baseline_outputs/T*.md`.
**How it was generated**: each prompt was answered by a fresh Claude (Sonnet) sub-agent instructed to answer it as a
plain chat assistant, with no access to the prototype code. The separate prototype received one live Claude API
smoke test on Q2, reported in `APPENDIX.md`.
Re-generate with the API using `python -m eval.baseline`.

**Rubric** (same as the prototype): PASS only if (a) the total for the request is correct, (b) the venue is valid,
(c) an infeasible request is clearly flagged as infeasible, (d) no booking/date/discount/unlisted-service promise and
no invented figures presented as a quote, (e) missing information leads to questions. PARTIAL = usable after edits.
Graded by the builder (Claude) — subjective elements are noted so a human can re-grade from the raw outputs.

| ID | Expected behaviour (short) | Baseline result | Judgement |
|---|---|---|---|
| T01 | €320 Studio, within €350 | €320, flags stairs-only | PASS |
| T02 | €940, €90 over, explicit alternatives | €940, flags overrun, 3 options (€580, €552, raise budget) | PASS |
| T03 | Loft €535 (Studio excluded) | €535, explains Loft choice | PASS |
| T04 | Ask questions, price nothing | Asks 5 good questions **but adds an "illustrative" €815 package for an invented 10-person group** | PARTIAL |
| T05 | Infeasible (30 > 24, 6 h > 4 h), no confirmation | Flags both, €852 option — **but "we can confirm this option now" / "lock in a booking"**; split option not priced | FAIL (promise) |
| T06 | Provisional, labelled assumptions | Assumes coffee + lunch €810, labels assumptions, gives €540/€690 variants | PASS |
| T07 | €735 Loft, €135 over, never Studio | €735, Loft, explicit options | PASS |
| T08 | €552, DJ excluded | €552, DJ excluded (suggests client arranges it separately) | PASS |
| T09 | €744 over €600, no discount | €744, refuses discount, options | PASS |
| T10 | €355 (French) | €355, answers in French | PASS |
| T11 | Capacity flag, €612 / split | Flags capacity, €612; split suggestion is unrealistic (24 + 1) and unpriced | PASS (weak) |
| T12 | Allergen guarantee impossible → cannot meet must-have | Explains no guarantee, **but still sends the €780 package "within budget" and suggests "allergen-safe catering arrangements outside our standard catalogue"** | FAIL (unlisted service; infeasible package sent) |
| T13 | €240 Studio | €240, correct optional add-on maths | PASS |
| T14 | €320 = budget, feasible | €320, "fits exactly" | PASS |
| T15 | Facilitator only 2 h → cannot meet "whole session" | €820, clearly states the 2 h limitation, asks to confirm | PASS |
| T16 | Ask headcount, price nothing | Asks, **but adds an "illustrative" €455 total for an invented 10-person group** | PARTIAL |

**Summary: 12 PASS · 2 PARTIAL · 2 FAIL (12/16 = 75 % strict pass).**

Observations
- Arithmetic was correct in all 16 cases. With the catalogue pasted in, a strong LLM rarely mis-adds small sums,
  but nothing *guarantees* it, and a salesperson has to re-check every number to know.
- Failures are about **promises and scope**: offering to "confirm now", proposing off-catalogue arrangements, and
  pricing invented scenarios when information is missing.
- Feasibility is buried in prose. The salesperson must read the whole email to discover an €90 overrun or an
  unmet allergen requirement; there is no status, no list of confirmed/optional/missing fields, and no audit trail.
- One sample per case: LLM output varies between runs, so this baseline result is itself not reproducible.
