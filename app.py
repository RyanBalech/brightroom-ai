"""BrightRoom proposal assistant — Streamlit UI for the salesperson.

    streamlit run app.py
"""
import html
import json
import pathlib
import re

import streamlit as st

from brightroom import llm
from brightroom.catalogue import SERVICES, VENUES
from brightroom.draft import brief_table, eur
from brightroom.engine import INFEASIBLE, NEEDS_CLARIFICATION, PROVISIONAL, READY
from brightroom.pipeline import run

ROOT = pathlib.Path(__file__).parent
st.set_page_config(page_title="BrightRoom · Proposal assistant", page_icon="◐", layout="wide")

# ----------------------------------------------------------------------------- style
st.markdown("""
<style>
:root{
  --ink:#1f1f1d; --ink-2:#55544f; --ink-3:#8a8983; --line:#e4e2dc; --card:#ffffff; --tint:#f3f2ee;
  --brand:#3b3a8f; --brand-tint:#ecebf7;
  --good:#0ca30c; --good-tint:#e9f6e9; --warn:#fab219; --warn-tint:#fff6e0;
  --crit:#d03b3b; --crit-tint:#fbeaea; --info:#3b3a8f; --info-tint:#ecebf7;
}
.block-container{padding-top:1.4rem; max-width:1320px}
header[data-testid="stHeader"]{display:none}
.grp{font-size:.75rem; letter-spacing:.06em; color:var(--ink-3); font-weight:600; padding-top:8px}
h1,h2,h3{letter-spacing:-0.01em}
.hero{display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
  padding:18px 22px; border-radius:14px; background:linear-gradient(120deg,#2f2e78 0%,#3b3a8f 55%,#5552b8 100%);
  color:#fff; margin-bottom:14px}
.hero .t{font-size:1.55rem; font-weight:700; line-height:1.2}
.hero .s{opacity:.85; font-size:.95rem; margin-top:2px}
.badge{display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px; font-size:.8rem;
  font-weight:600; background:rgba(255,255,255,.16); color:#fff; border:1px solid rgba(255,255,255,.28)}
.stepper{display:flex; gap:6px; flex-wrap:wrap; margin:6px 0 14px}
.step{flex:1 1 140px; padding:8px 12px; border-radius:10px; background:var(--tint); color:var(--ink-3);
  font-size:.82rem; border:1px solid var(--line)}
.step b{display:block; color:var(--ink-2); font-size:.86rem}
.step.done{background:var(--card); color:var(--ink-2); border-color:#cfcde6}
.step.done b{color:var(--brand)}
.status{border-radius:14px; padding:16px 20px; border:1px solid var(--line); border-left:8px solid var(--c);
  background:var(--bg); margin:4px 0 12px}
.status .h{font-size:1.25rem; font-weight:700; color:var(--ink)}
.status .d{color:var(--ink-2); margin-top:4px; font-size:.95rem}
.kpis{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:14px}
.kpi{background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 14px}
.kpi .l{font-size:.78rem; color:var(--ink-3); text-transform:uppercase; letter-spacing:.04em}
.kpi .v{font-size:1.55rem; font-weight:700; color:var(--ink); margin-top:2px; font-variant-numeric:tabular-nums}
.kpi .n{font-size:.82rem; color:var(--ink-2); margin-top:2px}
.card{background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; margin-bottom:12px}
.card h4{margin:0 0 8px; font-size:.95rem; color:var(--ink)}
.chips{display:flex; flex-wrap:wrap; gap:6px}
.chip{font-size:.83rem; padding:4px 10px; border-radius:999px; border:1px solid var(--line); background:var(--tint);
  color:var(--ink)}
.chip.ok{background:var(--good-tint); border-color:#bfe3bf}
.chip.opt{background:var(--brand-tint); border-color:#d3d1ee}
.chip.miss{background:var(--warn-tint); border-color:#f3dc9f}
.issue{display:flex; gap:10px; padding:8px 0; border-top:1px solid var(--line); font-size:.9rem; color:var(--ink)}
.issue:first-child{border-top:none}
.issue .tag{font-weight:700; font-size:.72rem; letter-spacing:.04em; padding:2px 7px; border-radius:6px;
  white-space:nowrap; height:fit-content; color:var(--ink)}
.tag.blocker{background:var(--crit-tint); border:1px solid #efc4c4}
.tag.warning{background:var(--warn-tint); border:1px solid #f3dc9f}
.tag.info{background:var(--info-tint); border:1px solid #d3d1ee}
.alt{background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; height:100%}
.alt .top{display:flex; justify-content:space-between; align-items:baseline; gap:8px}
.alt .ti{font-weight:700; color:var(--ink); font-size:.95rem}
.alt .pr{font-weight:700; font-size:1.3rem; color:var(--ink); font-variant-numeric:tabular-nums}
.alt ul{margin:8px 0 0 0; padding-left:18px; color:var(--ink-2); font-size:.86rem}
.fit{font-size:.75rem; font-weight:600; padding:2px 8px; border-radius:999px; color:var(--ink)}
.fit.y{background:var(--good-tint); border:1px solid #bfe3bf}
.fit.n{background:var(--crit-tint); border:1px solid #efc4c4}
.flow{display:flex; align-items:stretch; gap:8px; flex-wrap:wrap; margin:6px 0 16px}
.flow .b{flex:1 1 150px; border-radius:12px; padding:12px; border:1px solid var(--line); background:var(--card);
  font-size:.86rem; color:var(--ink-2)}
.flow .b b{display:block; color:var(--ink); margin-bottom:4px}
.flow .b.ai{border-color:#d3d1ee; background:var(--brand-tint)}
.flow .b.hu{border-color:#bfe3bf; background:var(--good-tint)}
.flow .ar{align-self:center; color:var(--ink-3); font-size:1.2rem}
.muted{color:var(--ink-3); font-size:.85rem}
div[data-testid="stTabs"] button p{font-size:1rem; font-weight:600}
.st-key-draftbox h4{font-size:1.02rem !important; margin-top:.6rem}
.st-key-draftbox table{font-size:.88rem}
</style>
""", unsafe_allow_html=True)

STATUS_STYLE = {
    READY: ("✅", "Feasible — ready for your review", "Every requirement is met from the catalogue.",
            "var(--good)", "var(--good-tint)"),
    PROVISIONAL: ("⚠️", "Provisional — check the labelled assumptions",
                  "Feasible, but some details were not stated. Confirm the assumptions or ask the questions.",
                  "var(--warn)", "var(--warn-tint)"),
    INFEASIBLE: ("⛔", "Cannot meet the brief as stated — do not send as-is",
                 "At least one requirement cannot be met. Offer the alternatives; each one names its trade-off.",
                 "var(--crit)", "var(--crit-tint)"),
    NEEDS_CLARIFICATION: ("❓", "Clarification needed — no prices yet",
                          "Key information is missing; quoting now would mean inventing numbers. Send the questions.",
                          "var(--info)", "var(--info-tint)"),
}

CASES = {c["id"]: c for c in json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))}
SAMPLE_GROUPS = {
    "Routine": [("T03", "Q3 · wheelchair + projector"), ("T01", "Q1 · 10 people, coffee"), ("T10", "Français")],
    "Difficult": [("T02", "Q2 · over budget"), ("T05", "Q5 · 30 people, 6 h"), ("T07", "Wheelchair trap"),
                  ("T12", "Allergen guarantee")],
    "Missing info": [("T04", "Q4 · 'best offer'"), ("T06", "'about 15, with food'"), ("T08", "DJ request")],
}
e = html.escape


def chips(items, cls):
    return '<div class="chips">' + "".join(f'<span class="chip {cls}">{e(x)}</span>' for x in items) + "</div>" \
        if items else '<span class="muted">—</span>'


def md_inline(s: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e(s))


# ----------------------------------------------------------------------------- header
can_llm = llm.llm_available()
mode = f"Claude mode · {llm.MODEL}" if can_llm else "Rules mode · offline, deterministic"
st.markdown(f"""<div class="hero"><div><div class="t">◐ BrightRoom · Proposal assistant</div>
<div class="s">Client enquiry → structured brief → checked draft proposal, or the questions to ask first.</div></div>
<span class="badge">{'🤖' if can_llm else '⚙️'} {e(mode)}</span></div>""", unsafe_allow_html=True)

tab_app, tab_eval, tab_how = st.tabs(["✍️  Proposal assistant", "📊  Test evidence", "🧭  How it works"])

# ============================================================================= assistant
with tab_app:
    if "enquiry" not in st.session_state:
        st.session_state["enquiry"] = CASES["T03"]["enquiry"]
    # Deep link for the demo: ?case=T02 loads and runs that test enquiry once.
    qcase = st.query_params.get("case")
    if qcase in CASES and st.session_state.get("qcase_done") != qcase:
        st.session_state["qcase_done"] = qcase
        st.session_state["enquiry"] = CASES[qcase]["enquiry"]
        st.session_state["out"] = run(CASES[qcase]["enquiry"], use_llm=llm.llm_available())
        st.session_state["approved"] = False

    for group, items in SAMPLE_GROUPS.items():
        g1, g2 = st.columns([1, 8], vertical_alignment="center")
        g1.markdown(f'<div class="grp">{group.upper()}</div>', unsafe_allow_html=True)
        with g2:
            pick = st.pills(group, [lbl for _, lbl in items], key=f"pill_{group}", label_visibility="collapsed")
            if pick and st.session_state.get(f"last_{group}") != pick:
                st.session_state[f"last_{group}"] = pick
                st.session_state["enquiry"] = CASES[dict((lbl, i) for i, lbl in items)[pick]]["enquiry"]
                st.session_state.pop("out", None)

    c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
    with c1:
        enquiry = st.text_area("Client enquiry", key="enquiry", height=90,
                               placeholder="e.g. A team day for about 15 people, with food, within a modest budget.")
    with c2:
        use_llm = st.toggle("Use Claude", value=can_llm, disabled=not can_llm,
                            help="Claude reads the enquiry and writes the cover note. Prices, venue and feasibility "
                                 "are always computed by code. Needs ANTHROPIC_API_KEY.")
        go = st.button("Prepare draft  →", type="primary", use_container_width=True, disabled=not enquiry.strip())
    if go:
        with st.spinner("Reading the enquiry and checking it against the catalogue…"):
            st.session_state["out"] = run(enquiry, use_llm=use_llm)
        st.session_state["approved"] = False

    out = st.session_state.get("out")
    steps = [("1 · Enquiry", "free text in"), ("2 · Brief", "confirmed · optional · missing"),
             ("3 · Checks", "catalogue rules, budget"), ("4 · Draft", "package or questions"),
             ("5 · Approval", "salesperson decides")]
    done = 0 if not out else (5 if st.session_state.get("approved") else 4)
    st.markdown('<div class="stepper">' + "".join(
        f'<div class="step {"done" if i < done else ""}"><b>{"✓ " if i < done else ""}{a}</b>{b}</div>'
        for i, (a, b) in enumerate(steps)) + "</div>", unsafe_allow_html=True)

    if not out:
        st.info("Pick a sample above or paste an enquiry, then click **Prepare draft**.")
    else:
        r = out.result
        icon, title, desc, c, bg = STATUS_STYLE[r.status]
        blockers = "".join(f"<div class='d'>⛔ {md_inline(i.message)}</div>" for i in r.blockers)
        st.markdown(f'<div class="status" style="--c:{c};--bg:{bg}"><div class="h">{icon} {title}</div>'
                    f'<div class="d">{desc}</div>{blockers}</div>', unsafe_allow_html=True)

        b = r.brief
        if r.budget_margin is None:
            margin_v, margin_n = "—", ("budget not stated" if b.budget_eur is None else "no package")
        elif r.budget_margin >= 0:
            margin_v, margin_n = f"▲ {eur(r.budget_margin)}", "under budget"
        else:
            margin_v, margin_n = f"▼ {eur(-r.budget_margin)}", "OVER budget"
        venue = VENUES[r.package.venue_id].name if r.package else "—"
        tiles = [("Package total", eur(r.package.total) if r.package else "—",
                  f"{venue} · {r.package.headcount} people" if r.package else "not priced"),
                 ("Client budget", eur(b.budget_eur) if b.budget_eur is not None else "—",
                  "stated" if b.budget_eur is not None else (b.budget_vague or "not stated")),
                 ("Budget margin", margin_v, margin_n),
                 ("Blocking issues", str(len(r.blockers)), "must be resolved" if r.blockers else "none"),
                 ("Open questions", str(len(r.questions)), "for the client" if r.questions else "none")]
        st.markdown('<div class="kpis">' + "".join(
            f'<div class="kpi"><div class="l">{a}</div><div class="v">{v}</div><div class="n">{e(n)}</div></div>'
            for a, v, n in tiles) + "</div>", unsafe_allow_html=True)

        left, right = st.columns([1, 1.15], gap="large")
        with left:
            confirmed, optional, missing = brief_table(b)
            st.markdown(f"""<div class="card"><h4>Structured brief</h4>
              <div class="muted" style="margin-bottom:6px">✅ Confirmed requirements</div>{chips(confirmed, 'ok')}
              <div class="muted" style="margin:10px 0 6px">➕ Optional / other requests</div>{chips(optional, 'opt')}
              <div class="muted" style="margin:10px 0 6px">❓ Missing information</div>{chips(missing, 'miss')}
              </div>""", unsafe_allow_html=True)

            rows = [(i.severity, i.code, i.message) for i in r.issues]
            rows += [("info", "EXTRACTION", w) for w in b.extraction_warnings]
            rows += [("warning", "ASSUMPTION", a) for a in r.assumptions]
            rows += [("info", "NOTE", n) for n in r.notes]
            body = "".join(f'<div class="issue"><span class="tag {s}">{e(code)}</span><span>{md_inline(m)}</span></div>'
                           for s, code, m in rows) or '<span class="muted">Nothing to flag.</span>'
            st.markdown(f'<div class="card"><h4>Salesperson checks</h4>{body}</div>', unsafe_allow_html=True)
            for err in out.llm_errors:
                st.warning(err)
            if out.audit_violations:
                st.warning("Claude's cover note was rejected by the guardrail and replaced by the template: "
                           + "; ".join(out.audit_violations))
            with st.expander("Evidence — the words each value came from"):
                st.json(b.evidence or {}, expanded=True)
                st.caption(f"Extractor: {b.extractor} · prepared in {out.seconds:.2f} s")

        with right:
            st.markdown(f"**Client draft** <span class='muted'>· figures by the pricing engine · cover note: "
                        f"{e(out.cover_source)}</span>", unsafe_allow_html=True)
            with st.container(border=True, height=560, key="draftbox"):
                st.markdown(out.client_md)

        if r.alternatives:
            st.markdown("#### Alternatives — each one changes the client's request")
            acols = st.columns(min(3, len(r.alternatives)))
            for k, a in enumerate(r.alternatives[:6]):
                fit = "" if a.fits_budget is None else (
                    '<span class="fit y">within budget</span>' if a.fits_budget else '<span class="fit n">above budget</span>')
                must = "⚠️ changes the client's request" if a.must_have_changes else "keeps every requirement"
                with acols[k % len(acols)]:
                    st.markdown(f'<div class="alt"><div class="top"><span class="ti">Option {k + 1} · {e(a.title)}</span>'
                                f'<span class="pr">{eur(a.total)}</span></div><div style="margin-top:6px">{fit} '
                                f'<span class="muted">{must}</span></div><ul>'
                                + "".join(f"<li>{e(x)}</li>" for x in a.changes) + "</ul></div>",
                                unsafe_allow_html=True)

        st.divider()
        st.markdown("#### Salesperson approval")
        ack_text = "I have reviewed the figures, assumptions and flags"
        if r.status == INFEASIBLE:
            ack_text += " — and I understand the brief cannot be met as stated"
        elif r.status == NEEDS_CLARIFICATION:
            ack_text += " — this message asks questions and contains no quote"
        a1, a2 = st.columns([3, 1], vertical_alignment="center")
        with a1:
            ack = st.checkbox(ack_text, key=f"ack_{hash(out.enquiry)}")
        with a2:
            if st.button("Approve draft", disabled=not ack, use_container_width=True):
                st.session_state["approved"] = True
                st.rerun()
        if st.session_state.get("approved"):
            st.success("Approved. Nothing has been sent or booked — copy or download the text and send it yourself "
                       "after the availability check.")
            st.download_button("⬇ Download draft (.md)", out.client_md, file_name="brightroom_draft.md")
            st.code(out.client_md, language="markdown")

# ============================================================================= evidence
with tab_eval:
    st.markdown("#### Does it work? Same enquiries, single-prompt baseline vs prototype")
    tiles = [("Designed tests (16)", "16 / 16", "prototype · re-run live below"),
             ("Single-prompt baseline", "12 / 16", "2 partial · 2 fail"),
             ("Forbidden promises", "4 → 0", "baseline → prototype"),
             ("Blind set 1 (first run)", "5 / 10", "all misses = extraction"),
             ("Blind set 2 (first run)", "7 / 10", "6 / 10 strictly")]
    st.markdown('<div class="kpis">' + "".join(
        f'<div class="kpi"><div class="l">{a}</div><div class="v">{v}</div><div class="n">{n}</div></div>'
        for a, v, n in tiles) + "</div>", unsafe_allow_html=True)
    st.caption("Baseline totals were correct in 16/16 cases; its failures were promises and scope ('we can confirm "
               "this now', off-catalogue allergen catering, invented 'illustrative' packages). Blind sets were written "
               "by independent agents that never saw the code; after fixing the extraction gaps they found, both pass "
               "10/10 (no longer blind).")

    if st.button("▶ Re-run all 36 tests now", type="primary"):
        from eval.run_eval import check
        rows, summary = [], {}
        for fname, label in [("cases.json", "Designed"), ("heldout_cases.json", "Blind 1"), ("blind2_cases.json", "Blind 2")]:
            cs = json.loads((ROOT / "eval" / fname).read_text(encoding="utf-8"))
            ok_n = 0
            for c in cs:
                o = run(c["enquiry"], use_llm=False)
                ok, fails = check(c, o)
                ok_n += ok
                rows.append({"Set": label, "ID": c["id"], "Type": c["type"], "Status": o.result.status,
                             "Total": eur(o.result.package.total) if o.result.package else "—",
                             "Result": "✅ PASS" if ok else "❌ " + "; ".join(fails)})
            summary[label] = f"{ok_n}/{len(cs)}"
        st.success("  ·  ".join(f"{k}: **{v}**" for k, v in summary.items()) + "  — deterministic, rules mode")
        st.dataframe(rows, hide_index=True, use_container_width=True)

    base = {}
    for line in (ROOT / "eval" / "results_baseline.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| (T\d+) \|.*\| ([^|]+) \|$", line)
        if m:
            base[m.group(1)] = m.group(2).strip()
    proto = {d["id"]: d for d in json.loads((ROOT / "eval" / "results_prototype.json").read_text(encoding="utf-8"))}
    table = [{"ID": cid, "Enquiry": c["enquiry"], "Expected": c["expected"]["behaviour"],
              "Baseline": base.get(cid, "—"),
              "Prototype": ("PASS · " if proto[cid]["pass"] else "FAIL · ") + proto[cid]["status"]}
             for cid, c in CASES.items()]
    st.markdown("##### Designed test set — baseline vs prototype")
    st.dataframe(table, hide_index=True, use_container_width=True,
                 column_config={"Enquiry": st.column_config.TextColumn(width="large"),
                                "Expected": st.column_config.TextColumn(width="large")})

# ============================================================================= how it works
with tab_how:
    st.markdown("#### One workflow, three kinds of worker")
    st.markdown("""<div class="flow">
      <div class="b ai"><b>🤖 Read (GenAI)</b>Enquiry → brief. Every number must quote the enquiry; cross-checked by rules.</div>
      <div class="ar">→</div>
      <div class="b"><b>⚙️ Decide (code)</b>Venue, capacity, access, 4 h limit, prices, totals, budget, status.</div>
      <div class="ar">→</div>
      <div class="b"><b>⚙️ Alternatives (code)</b>Re-priced variants, each listing what changes vs the brief.</div>
      <div class="ar">→</div>
      <div class="b ai"><b>🤖 Write (GenAI)</b>Short cover note — audited for invented prices &amp; promises.</div>
      <div class="ar">→</div>
      <div class="b hu"><b>🧑 Approve (human)</b>Review flags, approve, check availability, send.</div>
    </div>""", unsafe_allow_html=True)
    h1, h2 = st.columns(2, gap="large")
    with h1:
        st.markdown("""
**When does it ask instead of quoting?**
- 🔵 **No headcount** → questions only; any price would be invented.
- 🟡 **Bounded gaps** (no budget, "about 15", "with food", duration, access unknown with the stairs-only Studio)
  → provisional draft, every assumption labelled.
- 🔴 **A stated need can't be met** (> 24 people, > 4 h, over budget, facilitator > 2 h, allergen guarantee,
  must-have outside the catalogue) → no package presented as valid; alternatives with trade-offs.

**What it never does:** confirm a booking or date, offer a discount, add an unlisted service, or silently drop a
must-have to make the numbers work.
""")
    with h2:
        st.markdown("""
**Use it from Claude (MCP server)**

`python -m brightroom.mcp_server` exposes the engine to Claude Desktop / Claude Code:

| Tool | Does |
|---|---|
| `analyse_enquiry` | enquiry → brief, status, package, alternatives, questions |
| `price_brief` | price a brief the host LLM extracted |
| `check_draft` | audit any message for invented € or promises |
| `get_catalogue` | the approved catalogue |

Claude handles the conversation; the tools guarantee every number.
""")
    st.markdown("##### Approved catalogue")
    st.dataframe([{"ID": v.id, "Item": v.name, "Price": eur(v.price), "Conditions": v.notes} for v in VENUES.values()]
                 + [{"ID": s.id, "Item": s.name, "Price": eur(s.price) + ("/person" if s.per_person else ""),
                     "Conditions": s.notes} for s in SERVICES.values()], hide_index=True, use_container_width=True)
