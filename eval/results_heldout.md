# Heldout results — 10/10 pass (extractor: rules, total runtime 0.01s)

| ID | Type | Expected behaviour | Prototype result | Judgement |
|---|---|---|---|---|
| H01 | routine feasible (Studio, accessibility waived) | Cheapest compliant venue is Studio: 240 + coffee 10x8=80 + lunch 10x18=180 + projector 35 = 535 <= 700, stairs explicitly OK so nothing material is missing. | READY_FOR_REVIEW; total €535 | PASS |
| H02 | routine feasible (Loft by capacity) | 20 > 12 so Loft: 420 + coffee 20x8=160 + facilitator 280 = 860 <= 1200; Loft is accessible so accessibility needs no assumption. | READY_FOR_REVIEW; total €860 | PASS |
| H03 | missing info: no headcount | Headcount is unknown so per-person lunch and venue choice cannot be priced; the tool should ask for the number of attendees (and duration/budget/accessibility) rather than produce a package. | NEEDS_CLARIFICATION; total — | PASS |
| H04 | missing info: approximate headcount, no duration, no budget | ~15 > 12 so Loft: 420 + projector 35 = 455; headcount is approximate, duration and budget are not stated, so the draft must be provisional. | PROVISIONAL; total €455 | PASS |
| H05 | French, wheelchair user | Wheelchair user rules out stairs-only Studio, so Loft: 420 + café 8x8=64 + déjeuner 8x18=144 = 628 <= 800; vegetarian lunch is available on request. | READY_FOR_REVIEW; total €628 | PASS |
| H06 | over budget | 22 > 12 so Loft: 420 + coffee 22x8=176 + lunch 22x18=396 + projector 35 = 1027 > 900, and no discounts are allowed, so the budget cannot be met. | INFEASIBLE; total €1027; alts €897, €851, €631, €1027 | PASS |
| H07 | tricky accessibility (cheap Studio tempting but excluded) | Studio (240 + 48 = 288) would fit the budget but is stairs-only, so Loft is required: 420 + coffee 6x8=48 = 468 > 300, budget below the cheapest compliant package. | INFEASIBLE; total €468; alts €468 | PASS |
| H08 | must-have service not in catalogue | The catalogue part fits the Studio (12 <= 12): 240 + coffee 12x8=96 = 336, but the must-have video recording is not offered, so the request as stated cannot be fulfilled. | INFEASIBLE; total €336; alts €336 | PASS |
| H09 | numbers as words / 1.2k formatting | Fifteen > 12 so Loft: 420 + lunch 15x18=270 + facilitator 280 = 970 <= 1200 (1.2k); Loft is accessible and all details are stated. | READY_FOR_REVIEW; total €970 | PASS |
| H10 | allergen guarantee with catering | Studio fits (9 <= 12, stairs OK): 240 + lunch 9x18=162 = 402 <= 500, but BrightRoom gives no allergen guarantee, so the stated requirement cannot be met. | INFEASIBLE; total €402; alts €402, €240 | PASS |
