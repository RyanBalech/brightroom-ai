# Blind2 results — 7/10 pass (extractor: rules, total runtime 0.01s)

| ID | Type | Expected behaviour | Prototype result | Judgement |
|---|---|---|---|---|
| H11 | exactly 12 (a dozen), Studio, stairs OK | 12 people fits the Studio (max 12, stairs confirmed OK): 240 + coffee 12x8=96 + lunch 12x18=216 + projector 35 = 587 <= 700; vegetarian on request is fine; date needs separate availability check. | READY_FOR_REVIEW; total €587 | PASS |
| H12 | exactly 24, wheelchair, full package | 24 people at the capacity limit and wheelchair access -> Loft: 420 + coffee 24x8=192 + lunch 24x18=432 + projector 35 + facilitator 280 = 1359 <= 1500. | PROVISIONAL; total €1359 | FAIL: status PROVISIONAL not in ['READY_FOR_REVIEW'] |
| H13 | budget per head, over budget | 15 people needs the Loft: 420 + (8+18)x15=390 = 810, but the budget is 40x15 = 600, so 810 > 600 and the request is over budget; no discount may be offered. | INFEASIBLE; total €810; alts €810 | PASS |
| H14 | French/English mix, no lunch | 10 people with stairs explicitly fine -> Studio: 240 + coffee 10x8=80 + projector 35 = 355 <= 900; lunch must NOT be included. | PROVISIONAL; total €355 | FAIL: status PROVISIONAL not in ['READY_FOR_REVIEW'] |
| H15 | long rambling, 30 people | 30 people exceeds the Loft maximum of 24 and only one venue per booking is allowed (and the group must stay together), so no package can be priced. | INFEASIBLE; total —; alts €1324, €2180 | PASS |
| H16 | optional non-catalogue item 'if possible' | 18 people needs the Loft: 420 + coffee 18x8=144 = 564 <= 1000; the photographer is not in the catalogue and is optional, so it is excluded and flagged, not priced. | READY_FOR_REVIEW; total €888 | FAIL: status READY_FOR_REVIEW not in ['PROVISIONAL']; total 888 != 564 |
| H17 | budget exactly equals total | Loft for 20 with wheelchair access: 420 + (8+18)x20=520 + projector 35 = 975, exactly equal to the 975 budget so within budget; date needs separate availability check. | READY_FOR_REVIEW; total €975 | PASS |
| H18 | headcount unknown, typos | Headcount is unknown so venue and per-person services cannot be priced; the tool must ask how many people will attend rather than quote. | NEEDS_CLARIFICATION; total — | PASS |
| H19 | approximate headcount | Priced at 22 people in the Loft: 420 + (8+18)x22=572 = 992 <= 1200 (even 24 would be 420+624=1044 <= 1200), but the headcount is approximate so the proposal is provisional. | PROVISIONAL; total €992 | PASS |
| H20 | allergen guarantee with lunch | Studio for 9 (stairs fine): 240 + (8+18)x9=234 = 474 <= 600, but the lunch has no allergen guarantee and the client requires one, so the request is infeasible as stated. | INFEASIBLE; total €474; alts €474, €240 | PASS |
