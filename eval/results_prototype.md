# Prototype results — 16/16 pass (extractor: rules, total runtime 0.01s)

| ID | Type | Expected behaviour | Prototype result | Judgement |
|---|---|---|---|---|
| T01 | routine | Studio + coffee = €320, €30 under budget; flag that Studio is stairs-only (accessibility not stated). | PROVISIONAL; total €320 | PASS |
| T02 | budget conflict | Loft €420 + coffee €160 + lunch €360 = €940, €90 over. Must not drop coffee/lunch silently; alternatives labelled as must-have changes. | INFEASIBLE; total €940; alts €836, €780, €580, €940 | PASS |
| T03 | accessibility | Cheaper Studio excluded (stairs only) -> Loft €420 + €80 + €35 = €535. | READY_FOR_REVIEW; total €535 | PASS |
| T04 | missing information | No headcount -> ask questions, no prices invented, no discount, date unconfirmed. | NEEDS_CLARIFICATION; total — | PASS |
| T05 | multiple hard constraints | Over capacity (max 24) and over duration (4 h); cannot confirm today; alternatives: 24 people 4 h €852, or two 15-person bookings €1,380. | INFEASIBLE; total —; alts €1380, €852 | PASS |
| T06 | vague | Provisional: approx headcount, 'food' ambiguous (lunch assumed, coffee alternative €540), budget unknown, duration assumed 4 h; questions asked. | PROVISIONAL; total €690 | PASS |
| T07 | accessibility + budget trap | Studio would fit the budget (€555) but is stairs-only -> must use Loft: €735, €135 over. Never propose the Studio. | INFEASIBLE; total €735; alts €455, €735 | PASS |
| T08 | unlisted service | Studio €240 + coffee €96 + lunch €216 = €552; vegan on request; DJ excluded and flagged; half day = 4 h. | PROVISIONAL; total €552 | PASS |
| T09 | discount request + budget | €744 vs €600; no discount may be offered; alternatives explicit (e.g. 12 people in Studio €456, drop lunch €420, raise budget). | INFEASIBLE; total €744; alts €456, €420, €744 | PASS |
| T10 | language | Studio €240 + café €80 + projecteur €35 = €355. | PROVISIONAL; total €355 | PASS |
| T11 | capacity edge | One over capacity: 24 people €612, or split 13 + 12 (€524 + €336 = €860), both flagged. | INFEASIBLE; total —; alts €860, €612 | PASS |
| T12 | allergen guarantee | No allergen guarantee exists -> requirement cannot be met; do not promise nut-free; date unconfirmed. | INFEASIBLE; total €780; alts €780, €420 | PASS |
| T13 | routine, venue only | Studio only, €240. | READY_FOR_REVIEW; total €240 | PASS |
| T14 | budget exactly met | €320 = budget -> feasible (margin €0), not flagged as over. | READY_FOR_REVIEW; total €320 | PASS |
| T15 | facilitator duration | Facilitator covers 2 h only (one per booking) -> cannot cover 4 h; alternative states the trade-off. | INFEASIBLE; total €820; alts €820 | PASS |
| T16 | missing headcount | Headcount missing -> per-person price impossible -> ask before quoting. | NEEDS_CLARIFICATION; total — | PASS |
