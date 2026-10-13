# Demo video script (target 4 minutes)

Setup before recording: set `ANTHROPIC_API_KEY` locally, leave `BRIGHTROOM_OFFLINE` unset, then run
`streamlit run app.py` with the browser at full width (zoom 90 %). Select cases in the app; demo deep links run
automatically and would make extra API calls. Use Claude only for T02; switch it off for the other cases.
The **Test evidence** tab has a live "Re-run all 36 tests" button for the results section.

---

**0:00–0:30 · Problem, user, value target**
> "BrightRoom's salesperson turns informal enquiries like *'a team day for about 15 people, with food, within a
> modest budget'* into proposals by hand: clarify, check a short catalogue, calculate, write. It's repetitive and
> error-prone, and the worst failure is a polished proposal that silently breaks the brief. Our user is the
> salesperson; our EDGE target is **Efficiency** with **Decision** support: a first draft in seconds, with
> feasibility visible *before* sending."

**0:30–1:10 · Solution choice (show the sidebar + one-line architecture)**
> "We built an **Assistant-style Application** (5A): a small workflow, not an autonomous agent. GenAI does the
> language work: reading messy enquiries (English or French) into a structured brief and writing the covering
> paragraph. **Code** does everything that must be exactly right: venue choice, capacity, accessibility, duration,
> prices, totals, budget check, alternatives. Every LLM-extracted number must be backed by a quote from the enquiry,
> and the LLM's text is audited for invented prices, discounts or booking promises. The salesperson approves
> every draft. An agent would add cost and unpredictability without adding value for a six-item catalogue."

**1:10–1:50 · Routine case (T03, wheelchair)**
- Select *T03*, switch **Use Claude** off, and click **Prepare draft**. Point at: 🟢 status, the brief split into confirmed/optional/missing,
  *"Studio is cheaper but excluded: stairs only"*, itemised table €535, margin €65.
- Tick the review box, then **Approve**: "Nothing is sent or booked; the salesperson copies the text."

**1:50–3:00 · Difficult / failure cases**
- Select *T02*, switch **Use Claude** on, and click **Prepare draft**. Open **Evidence** to show
  `Extractor: llm+rules`; point at `cover note: llm` and 🔴 **€90 OVER budget**. "The tool never silently drops coffee or lunch. Each alternative
  states its trade-off: 16 people, or no coffee, or no lunch, or raise the budget, and each is marked as changing a
  must-have."
- Switch **Use Claude** off. Select *T05* (30 people, 6 h, "confirm today") and click **Prepare draft**: two blockers
  and the *cannot confirm* warning. Alternatives: 24 people
  for 4 h (€852), or two separate 15-person bookings (€1,380), each with its trade-offs.
- Select *T04* ("best offer next month") and click **Prepare draft**: 🔵 no prices at all, just the five questions to ask. "Here the baseline
  invented an 'illustrative' 10-person package."
- (Optional) Type a new enquiry live, e.g. *"We're about 9, one person uses crutches, coffee please, €300"* → Loft
  required, over budget, never the Studio.

**3:00–3:45 · Evidence**
- Open the **Test evidence** tab, click **Re-run all 36 tests now** (all pass in under a second), and scroll the
  baseline vs prototype table.
> "On 16 designed tests the prototype passes 16 out of 16; the single-prompt baseline passes 12, with 2 partial and
> 2 failures. The baseline's arithmetic was right every time; its failures were promises and scope: 'we can confirm
> this now', off-catalogue allergen catering, invented illustrative packages. On an independent held-out set the
> first blind run scored 5/10. Every miss was an extraction gap in the offline rules, not a pricing error. We fixed
> those, then ran a second, untouched blind set once: 7 out of 10, or 6 strictly, because one pass was right for the wrong reason. Again every miss was extraction, never pricing."

**(optional, +20 s) MCP:** "The same engine is also an MCP server, so a salesperson can work inside Claude
Desktop: Claude talks, but every price comes from `price_brief`, and every message passes `check_draft`."
Show the How it works tab.

**3:45–4:00 · Limitations and next step**
> "The rules extractor is brittle on open-vocabulary requests; that's where the Claude extractor comes in, and it's
> cross-checked against the rules. Our live Claude API check of Q2 passed with the correct €940 total and no audit
> violations. Next: evaluate more live enquiries, measure review time, and add availability checks."
