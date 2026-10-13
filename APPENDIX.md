# Appendix · Case 02 — From a client enquiry to a feasible proposal

**Team:** Romaissae Melhaoui · Ryan Balech  
**Contributions:** both members worked together on every part — scoping, design, building the prototype, testing and the demo video (prototype built with Claude Code as coding assistant).
**Tools used:** Claude Code (Claude Opus 5.5) for building; Python 3.13, Streamlit 1.65, Anthropic Python SDK 1.13, MCP Python SDK 2.3;
runtime LLM (optional) `claude-opus-5`.
**Data:** the fictional catalogue and enquiries Q1–Q5 from the case pack. Every other enquiry is a labelled
addition (T06–T16 written by us; H01–H20 written by independent agents that never saw our code).

---

## 1 · Design rationale

### User, workflow, value target
- **User:** BrightRoom's salesperson, who receives informal enquiries and must reply with a correct proposal or
  the right questions.
- **Workflow:** enquiry → structured brief → feasibility check → draft (package / alternatives / questions) →
  **salesperson review and approval** → salesperson sends.
- **EDGE target: Efficiency**, with **Decision** support. A first draft in seconds instead of a manual
  clarify-calculate-write cycle, and a status that shows *before sending* whether the brief can be met.
- **Success measures:** constraint satisfaction, correct totals, useful clarification (no invented figures), no
  forbidden promises, and preparation time.

### 5A choice: an **Assistant / Application** (a fixed workflow, not an agent)
The task is a short pipeline with known steps and a six-item catalogue. An autonomous agent would add cost, latency
and unpredictability without adding capability. The business risk is *confident errors* (wrong total, silently
dropped must-have, promised date), so we kept control flow in code and used the LLM only where language
understanding helps.

| Work | Who does it | Why |
|---|---|---|
| Reading a messy enquiry (EN/FR, typos, "about 15", "with food") into fields | **GenAI** (Claude, JSON-schema output), with a regex extractor as offline fallback and cross-check | Open-ended language; rules are brittle on unseen phrasing (see blind test 1) |
| Writing a warm cover paragraph in the client's language | **GenAI**, audited | Tone and language; low risk once figures are excluded |
| Venue choice, capacity, accessibility, 4-hour limit, 2-hour facilitator, per-person vs flat pricing, totals, budget check | **Code** (`engine.py`) | Must be exactly right and reproducible; trivially expressible as rules |
| Alternatives (reduce headcount, drop a service, split the group, raise budget) | **Code**, each re-priced by the same engine with every change listed | Prevents "making the numbers work" by silently changing a must-have |
| Feasibility status, what to ask, what not to promise | **Code** | Explicit, testable policy |
| Final judgement, editing, sending, availability check | **Human (salesperson)** | Accountability; availability is not in scope |

### MCP server (extension: the engine as tools for any Claude host)
`brightroom/mcp_server.py` publishes the same deterministic engine over the Model Context Protocol:
`analyse_enquiry`, `price_brief`, `check_draft`, `get_catalogue`, a `brightroom://catalogue` resource and a
`proposal_workflow` prompt. This keeps the core design rule when the salesperson works inside Claude Desktop or
Claude Code instead of the web app. Claude reads, converses and writes, but it must call the tools for every price
and must pass `check_draft` before presenting a message. All tools are read-only (no booking or sending
capability by design). Inputs are typed and validated (e.g. `services_required ∈ {S1..S4}`). Tested over stdio and
in-memory with the official MCP client (`tests/test_mcp_server.py`).

### Guardrails against confident errors
- The LLM **never produces a price**. All tables and totals are rendered by code, and the eval re-prices every
  package independently from the catalogue.
- **Grounding:** each LLM-extracted headcount, duration and budget must come with a verbatim quote from the enquiry
  that supports the number. If it doesn't, the value is discarded and the tool asks instead.
- **Cross-check:** in Claude mode, the rule extractor runs too. Disagreements become a visible "🔍 Extraction
  check" and the status cannot be 🟢.
- **Text audit:** the LLM cover note is rejected (template used instead) if it contains a euro amount the engine
  did not produce, a booking/date/availability promise, a discount, or an unlisted service not marked unavailable.
- **Never silently change a must-have:** every alternative lists its trade-offs, and the eval fails any alternative
  that drops a required service without naming it.
- **Accessibility is never traded away;** an alternative that moves to the stairs-only Studio says so when access
  needs are unknown.
- **Human control:** the UI requires ticking "I have reviewed…" before "Approve". Nothing is sent or booked.

### Decisions the case asked us to make
**When to ask vs. give a provisional proposal with labelled assumptions?**
- **Ask (no prices at all)** when the **headcount** is missing. Venue choice and every per-person price depend on
  it, so any number would be invented. (The baseline did exactly this with "illustrative" packages.)
- **Provisional proposal + questions** when the gap has a safe default or a bounded effect: duration missing →
  standard 4-hour block; approximate headcount → priced as stated; no or vague budget → fit not checked; "food" →
  lunch assumed, with the coffee-break total shown; accessibility not mentioned while the Studio (stairs) is chosen
  → asked explicitly. Each assumption is listed in the draft for the client to correct.
- **Infeasible** when a stated requirement cannot be met: over 24 people, over 4 hours, budget below the package,
  facilitator over 2 hours, allergen guarantee with catering, or a must-have outside the catalogue (including an
  *unrecognised* "non-negotiable" item, as a safety net).

**Which work benefits from GenAI, and which needs rules or code?** See the table above. In short: language in,
language out → GenAI; anything with a number or a yes/no constraint → code.

**How does the salesperson see that a polished proposal is infeasible before sending it?** A coloured status banner
and metrics row (total, budget, margin, open questions) appear *above* the draft. Blockers are listed with ⛔. An
infeasible draft says "does not meet the brief" in its headings, never shows an alternative as if it met the
request, and the approval checkbox wording changes to "I understand the brief cannot be met as stated".

---

## 2 · Reproduce the demo

See [README.md](README.md). In short: `pip install -r requirements.txt`, then `streamlit run app.py`, then pick a test
enquiry and click **Prepare draft**. Everything runs offline. Setting `ANTHROPIC_API_KEY` turns on Claude extraction
and the cover note. Prompts and schema: `brightroom/llm.py` (`EXTRACTION_SYSTEM`, `EXTRACTION_SCHEMA`,
`COVER_SYSTEM`). Baseline prompt: `eval/baseline.py`.

---

## 3 · Test evidence

### 3.1 Designed test set (16 cases: Q1–Q5 from the pack + 11 labelled variations)
Same inputs for baseline and prototype. Baseline = single prompt (catalogue + enquiry → "write a proposal with
itemised prices and a total"); raw outputs in `eval/baseline_outputs/`. Prototype = rules-only mode, deterministic.
Prototype checks are automated (`eval/run_eval.py`); baseline grading is a rubric judgement (see
`eval/results_baseline.md`).

| ID | Input (short) | Expected behaviour | Baseline (single prompt) | Prototype | Base | Proto |
|---|---|---|---|---|---|---|
| T01 | Q1 · 10 p, coffee, max €350 | Studio €320, €30 under | €320, flags stairs | 🟡 €320, asks about step-free access | PASS | PASS |
| T02 | Q2 · 20 p, coffee + lunch required, €850 | €940, €90 over; must-haves never silently dropped | €940 flagged, 3 options | 🔴 €940; alts €836 (16 p) / €780 / €580 / raise budget, each labelled | PASS | PASS |
| T03 | Q3 · 10 p, wheelchair, coffee, projector, €600 | Loft €535 (Studio excluded) | €535 | 🟢 €535, "Studio excluded: stairs only" | PASS | PASS |
| T04 | Q4 · "workshop next month, best offer" | Questions only, no prices, no discount | Good questions **+ invented €815 "illustrative" package** | 🔵 5 questions, no prices, discount and date flagged | PARTIAL | PASS |
| T05 | Q5 · 30 p, 6 h, lunch, €1,500, "confirm today" | Infeasible (capacity + duration), no confirmation | Flags both, €852 — **"we can confirm this option now"** | 🔴 2 blockers + "cannot confirm"; alts: 2 × 15 p €1,380 / 24 p €852 | FAIL | PASS |
| T06 | "about 15, with food, modest budget" | Provisional with labelled assumptions | Assumes coffee + lunch €810, labelled | 🟡 €690 (lunch assumed; coffee €540 shown), 4 questions | PASS | PASS |
| T07 | 8 p, 3 h, facilitator + projector, €600, wheelchair | Loft €735, €135 over; never the Studio | €735 + options | 🔴 €735, alts never use Studio | PASS | PASS |
| T08 | 12 p, half day, coffee + lunch, vegan, DJ "nice", €700 | €552, DJ excluded | €552, DJ excluded | 🟡 €552, DJ flagged, vegan noted | PASS | PASS |
| T09 | 18 p, lunch, max €600, "10% discount?" | €744 over; no discount | €744, refuses discount | 🔴 €744; alts €456 / €420 / raise | PASS | PASS |
| T10 | French · 10 p, café + projecteur, 400 € | €355 | €355 (in French) | 🟡 €355 | PASS | PASS |
| T11 | 25 p, coffee, €2,000 | Capacity blocker; 24 p / split | €612; unrealistic 24 + 1 split | 🔴 alts €612 / 13 + 12 split €860 | PASS (weak) | PASS |
| T12 | 20 p, lunch **guaranteed nut-free**, €1,000 | Cannot meet must-have; no off-catalogue promise | Explains no guarantee, **but sends €780 "within budget" and suggests off-catalogue allergen catering** | 🔴 ALLERGEN blocker; alts with/without catering | FAIL | PASS |
| T13 | 6 p, €300, no access needs | Studio €240 | €240 | 🟢 €240 | PASS | PASS |
| T14 | 10 p, coffee, budget **exactly** €320 | Feasible, margin 0 | €320 | 🟢 €320, margin €0 | PASS | PASS |
| T15 | facilitator "whole session" | 2 h only → cannot meet | €820, limitation stated | 🔴 FACILITATOR_HOURS blocker | PASS | PASS |
| T16 | no headcount, lunch + projector, €800 | Ask, don't price | Asks **+ invented €455 example** | 🔵 questions only | PARTIAL | PASS |
| | | | | **Total** | **12 PASS · 2 PARTIAL · 2 FAIL** | **16 / 16** |

### 3.2 Independent blind sets (generalisation, rules-only mode)
The designed set was written alongside the extractor, so it overstates robustness. Two independent agents wrote
10 enquiries each, with hand-computed expectations, without seeing our code.

| Set | First (blind) run | What failed | After fixing (no longer blind) |
|---|---|---|---|
| Held-out 1 (H01–H10) | **5 / 10** | All misses were **extraction**, never pricing: "nobody has mobility issues" read as a wheelchair need; "15 of us"; "fifteen"/"1.2k"; an open-vocabulary "non-negotiable video crew"; and the dangerous one, **"on crutches, can't do stairs" was missed, so the stairs-only Studio was proposed** (H07). | 10 / 10 |
| Blind 2 (H11–H20), run once after the fixes | **7 / 10** (strictly **6 / 10**: H13 had the right status for the wrong reason, "€40 per head" read as a €40 total) | "We'll sort our own lunch" priced as lunch (+€324, H16); "9:00 to 13:00" and French "l'escalier ne pose aucun problème" not recognised (safe-side: an unneeded question). Also seen: a split alternative offered although the client said splitting "defeats the point" (H15). | 10 / 10 |

**Reading:** the deterministic engine was right whenever the brief was right. Remaining risk sits in extraction of
unseen phrasing. That is exactly why the design puts Claude on extraction, with grounding and a rule cross-check,
and keeps a human approval step.

### 3.3 Quality, time and cost

| Measure | Manual (estimate) | Single-prompt baseline | Prototype |
|---|---|---|---|
| Correct totals (16 designed) | n/a | 16 / 16 (measured) | 16 / 16 and independently re-priced (measured) |
| Strict pass (rubric) | n/a | 12 / 16 = 75 % | 16 / 16 designed; 5/10 → 6–7/10 on blind runs (measured) |
| Forbidden promises / invented figures | n/a | 4 cases (T04, T05, T12, T16) | 0 (guardrail-tested) |
| Feasibility visible before reading prose | no | no (buried in text) | yes (status + metrics) |
| Preparation time per enquiry | ~10–20 min **(estimate, not measured)** | ~10–20 s generation + full read-through **(estimate)** | 0.01 s rules-only (measured); Claude mode ~5–15 s for 2 calls **(estimate, not measured)**; review ~2 min **(estimate)** |
| Running cost per enquiry | salesperson time | ~1 Opus call | €0 rules-only; Claude mode ≈ 2.5k input + 0.7k output tokens ≈ **$0.03 at Opus 5 list prices (estimate)** |
| Reproducibility | varies by person | varies run to run | deterministic engine; LLM only for extraction and prose |

### 3.4 Limitations (honest)
- **The Claude path was not run live in this sprint.** No API key was available on the build machine. It is
  implemented, schema-validated and unit-tested with a mocked client (grounding, cross-check, guardrail, API-failure
  fallback), but extraction quality with Claude is **unmeasured**. The baseline outputs were produced by Claude
  sub-agents answering the exact baseline prompt, not through the API.
- The rule extractor is brittle on unseen phrasing (blind runs above). It is a fallback, not the intended
  production extractor.
- Baseline: one sample per case, graded by the builder. Raw outputs are included so a human can re-grade.
- Out of scope by design: real availability, booking, payments, taxes, more than one venue per booking.

### 3.5 Next improvements
1. Run `python -m eval.run_eval` with `ANTHROPIC_API_KEY` set on all 36 cases and compare the rules vs Claude
   extraction accuracy.
2. Log real preparation and review time with the salesperson over a week of enquiries.
3. Add the open-vocabulary blind failures as regression cases (done for the fixed ones); grow the set from real
   enquiries.
