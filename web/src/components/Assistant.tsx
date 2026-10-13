import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight, Check, ChevronDown, ClipboardCheck, Copy, Download, FileText, Info, ListChecks, Loader2,
  MessageSquareText, Quote, ShieldAlert, ShieldCheck, Sparkles, TrendingDown, TrendingUp, TriangleAlert, UserCheck,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";
import { api, eur } from "../api";
import type { Analysis, Case, Health, Issue } from "../types";
import { AnimatedNumber, Chip, SectionTitle, STATUS, rise, stagger } from "./ui";

const GROUPS: { name: string; items: [string, string][] }[] = [
  { name: "Routine", items: [["T03", "Wheelchair + projector"], ["T01", "10 people, coffee"], ["T10", "En français"]] },
  { name: "Difficult", items: [["T02", "Over budget"], ["T05", "30 people, 6 hours"], ["T07", "Wheelchair trap"], ["T12", "Allergen guarantee"]] },
  { name: "Missing info", items: [["T04", "“Best offer”"], ["T06", "“About 15, with food”"], ["T08", "DJ request"]] },
];

const STEPS = [
  { icon: MessageSquareText, title: "Enquiry", sub: "free text in" },
  { icon: ListChecks, title: "Brief", sub: "confirmed · optional · missing" },
  { icon: ShieldCheck, title: "Checks", sub: "catalogue rules, budget" },
  { icon: FileText, title: "Draft", sub: "package or questions" },
  { icon: UserCheck, title: "Approval", sub: "salesperson decides" },
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Assistant({ cases, health }: { cases: Case[]; health: Health | null }) {
  const [enquiry, setEnquiry] = useState("");
  const [active, setActive] = useState<string | null>(null);
  const [useLlm, setUseLlm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [res, setRes] = useState<Analysis | null>(null);
  const [runId, setRunId] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [ack, setAck] = useState(false);
  const [approved, setApproved] = useState(false);
  const [copied, setCopied] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);
  const booted = useRef(false);

  useEffect(() => { if (health) setUseLlm(health.llm_available); }, [health]);

  async function prepare(text: string) {
    if (!text.trim() || loading) return;
    setLoading(true); setError(null); setRes(null); setAck(false); setApproved(false); setStep(1);
    try {
      const [data] = await Promise.all([
        api.analyse(text, useLlm && !!health?.llm_available),
        (async () => { await sleep(260); setStep(2); await sleep(260); setStep(3); await sleep(260); })(),
      ]);
      setRes(data); setRunId((n) => n + 1); setStep(4);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong"); setStep(0);
    } finally { setLoading(false); }
  }

  function pick(id: string, run = false) {
    const c = cases.find((x) => x.id === id);
    if (!c) return;
    setActive(id); setEnquiry(c.enquiry); setRes(null); setStep(0); setApproved(false); setAck(false);
    if (run) void prepare(c.enquiry);
  }

  // Deep link for the demo: ?case=T02 loads and runs that enquiry. Default sample otherwise.
  useEffect(() => {
    if (booted.current || !cases.length) return;
    booted.current = true;
    const q = new URLSearchParams(location.search).get("case");
    if (q && cases.some((c) => c.id === q)) pick(q, true); else pick("T03");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cases]);

  const done = approved ? 5 : step;

  return (
    <div className="space-y-6">
      <header>
        <div className="label mb-2">Proposal assistant</div>
        <h1 className="font-display text-[44px] leading-[1.05] tracking-tight text-ink">
          From a client enquiry to a <em className="text-brand-600">checked</em> proposal.
        </h1>
        <p className="mt-2 max-w-2xl text-[15px] text-ink-2">
          Paste what the client wrote. You get the brief, a feasibility status and a draft, or the questions to ask
          first. Prices and rules come from the catalogue engine, never from the AI.
        </p>
      </header>

      {/* Composer */}
      <motion.section layout className="card overflow-hidden">
        <div className="space-y-2.5 border-b border-line bg-canvas/60 px-5 py-4">
          {GROUPS.map((g) => (
            <div key={g.name} className="flex flex-wrap items-center gap-2">
              <span className="label w-24 shrink-0">{g.name}</span>
              {g.items.map(([id, label]) => (
                <motion.button
                  key={id} whileHover={{ y: -1 }} whileTap={{ scale: 0.97 }} onClick={() => pick(id)}
                  className={clsx(
                    "rounded-full px-3 py-1.5 text-[13px] font-medium ring-1 ring-inset transition-colors",
                    active === id ? "bg-brand-600 text-white ring-brand-600 shadow-sm"
                      : "bg-white text-ink-2 ring-line hover:ring-brand-500/40 hover:text-ink",
                  )}
                >{label}</motion.button>
              ))}
            </div>
          ))}
        </div>
        <div className="p-5">
          <textarea
            value={enquiry} rows={3}
            onChange={(e) => { setEnquiry(e.target.value); setActive(null); }}
            onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") void prepare(enquiry); }}
            placeholder="e.g. A team day for about 15 people, with food, within a modest budget."
            className="w-full resize-none rounded-xl border border-line bg-white px-4 py-3 text-[15px] leading-relaxed text-ink outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <label className={clsx("flex items-center gap-2.5 text-[13px]", health?.llm_available ? "text-ink-2 cursor-pointer" : "text-ink-3")}
              title={health?.llm_available ? "" : "Set ANTHROPIC_API_KEY to enable Claude. Everything works without it."}>
              <button type="button" role="switch" aria-checked={useLlm} disabled={!health?.llm_available}
                onClick={() => setUseLlm((v) => !v)}
                className={clsx("relative h-5 w-9 rounded-full transition-colors", useLlm ? "bg-brand-600" : "bg-line")}>
                <motion.span layout transition={{ type: "spring", stiffness: 600, damping: 32 }}
                  className={clsx("absolute top-0.5 h-4 w-4 rounded-full bg-white shadow", useLlm ? "right-0.5" : "left-0.5")} />
              </button>
              <Sparkles size={14} />
              {health?.llm_available ? "Claude reads the enquiry and writes the cover note" : "Claude mode off (no API key) · rules engine only"}
            </label>
            <motion.button
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }} disabled={!enquiry.trim() || loading}
              onClick={() => void prepare(enquiry)}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-[14px] font-semibold text-white shadow-[0_8px_20px_-8px_rgba(74,67,196,.7)] transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
              {loading ? "Checking…" : "Prepare draft"}
              <kbd className="ml-1 rounded bg-white/15 px-1.5 py-0.5 text-[10px] font-medium">⌘↵</kbd>
            </motion.button>
          </div>
        </div>
      </motion.section>

      {/* Stepper */}
      <div ref={resultRef} className="scroll-mt-6">
        <div className="relative grid grid-cols-5 gap-2">
          {STEPS.map((s, i) => {
            const on = i < done, current = loading && i === done;
            return (
              <motion.div key={s.title} animate={{ opacity: on || current ? 1 : 0.55 }}
                className={clsx("relative rounded-xl border px-3 py-2.5 transition-colors", on ? "border-brand-100 bg-white" : "border-line bg-white/50")}>
                <div className="flex items-center gap-2">
                  <motion.span animate={{ backgroundColor: on ? "#4a43c4" : "#e8e6ef", color: on ? "#fff" : "#8b8a96", scale: current ? [1, 1.12, 1] : 1 }}
                    transition={current ? { repeat: Infinity, duration: 0.9 } : { duration: 0.25 }}
                    className="grid h-6 w-6 place-items-center rounded-full">
                    {on ? <Check size={13} strokeWidth={3} /> : <s.icon size={12} />}
                  </motion.span>
                  <span className={clsx("text-[13px] font-semibold", on ? "text-ink" : "text-ink-3")}>{s.title}</span>
                </div>
                <div className="mt-1 truncate pl-8 text-[11.5px] text-ink-3">{s.sub}</div>
                {on && <motion.div layoutId={`bar-${i}`} initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.35 }}
                  className="absolute inset-x-3 bottom-0 h-0.5 origin-left rounded-full bg-brand-500" />}
              </motion.div>
            );
          })}
        </div>
      </div>

      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-[14px] text-rose-800">{error}</div>}

      <AnimatePresence mode="wait">
        {loading && (
          <motion.div key="sk" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
            {[72, 96, 220].map((h) => <div key={h} style={{ height: h }} className="animate-pulse rounded-2xl bg-white/70 ring-1 ring-line" />)}
          </motion.div>
        )}
        {!loading && !res && !error && (
          <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="rounded-2xl border border-dashed border-line bg-white/50 px-6 py-10 text-center text-[14px] text-ink-3">
            Pick a sample or paste an enquiry, then press <span className="font-semibold text-ink-2">Prepare draft</span>.
          </motion.div>
        )}
        {!loading && res && (
          <Result key={runId} res={res} ack={ack} setAck={setAck} approved={approved} setApproved={setApproved}
            copied={copied} onCopy={async () => { await navigator.clipboard.writeText(res.client_draft_markdown); setCopied(true); setTimeout(() => setCopied(false), 1600); }} />
        )}
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------------------------------------ */

const SEV: Record<Issue["severity"] | "assumption" | "note", { cls: string; icon: typeof Info }> = {
  blocker: { cls: "bg-rose-50 text-rose-800 ring-rose-200", icon: ShieldAlert },
  warning: { cls: "bg-amber-50 text-amber-800 ring-amber-200", icon: TriangleAlert },
  info: { cls: "bg-brand-50 text-brand-700 ring-brand-100", icon: Info },
  assumption: { cls: "bg-amber-50 text-amber-800 ring-amber-200", icon: TriangleAlert },
  note: { cls: "bg-canvas text-ink-2 ring-line", icon: Info },
};

function Result({ res, ack, setAck, approved, setApproved, copied, onCopy }: {
  res: Analysis; ack: boolean; setAck: (v: boolean) => void; approved: boolean; setApproved: (v: boolean) => void;
  copied: boolean; onCopy: () => void;
}) {
  const S = STATUS[res.status];
  const m = res.budget_margin_eur;
  const [showEvidence, setShowEvidence] = useState(false);
  const checks = [
    ...res.issues.map((i) => ({ kind: i.severity, code: i.code.replace(/_/g, " "), text: i.message })),
    ...res.assumptions.map((t) => ({ kind: "assumption" as const, code: "ASSUMPTION", text: t })),
    ...res.notes.map((t) => ({ kind: "note" as const, code: "NOTE", text: t })),
  ];
  const ackText = "I have reviewed the figures, assumptions and flags"
    + (res.status === "INFEASIBLE" ? ", and I understand the brief cannot be met as stated"
      : res.status === "NEEDS_CLARIFICATION" ? ". This message asks questions and contains no quote" : "");

  const download = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([res.client_draft_markdown], { type: "text/markdown" }));
    a.download = "brightroom_draft.md"; a.click(); URL.revokeObjectURL(a.href);
  };

  return (
    <motion.div variants={stagger} initial="hidden" animate="show" exit={{ opacity: 0, y: -8 }} className="space-y-5">
      {/* Status */}
      <motion.section variants={rise}
        className={clsx("relative overflow-hidden rounded-2xl bg-gradient-to-br p-5 ring-1", S.bg, S.ring)}>
        <div className="flex items-start gap-4">
          <motion.div initial={{ scale: 0, rotate: -30 }} animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 16, delay: 0.1 }}
            className={clsx("grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white shadow-sm ring-1", S.ring, S.fg)}>
            <S.icon size={22} />
          </motion.div>
          <div className="min-w-0">
            <h2 className="text-[19px] font-semibold tracking-tight text-ink">{S.title}</h2>
            <p className="mt-0.5 text-[14px] text-ink-2">{S.desc}</p>
            {res.issues.filter((i) => i.severity === "blocker").map((b, k) => (
              <motion.div key={k} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 + k * 0.08 }}
                className="mt-2 flex items-start gap-2 text-[14px] font-medium text-ink">
                <ShieldAlert size={16} className="mt-0.5 shrink-0 text-rose-600" />{b.message}
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* KPIs */}
      <motion.div variants={stagger} className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Kpi label="Package total" sub={res.package ? `${res.venue_name} · ${res.package.headcount} people` : "not priced"}>
          {res.package ? <AnimatedNumber value={res.package.total_eur} prefix="€" /> : "—"}
        </Kpi>
        <Kpi label="Client budget" sub={res.budget_eur != null ? "stated by client" : "not stated"}>
          {res.budget_eur != null ? <AnimatedNumber value={res.budget_eur} prefix="€" /> : "—"}
        </Kpi>
        <Kpi label="Budget margin" sub={m == null ? (res.budget_eur == null ? "budget not stated" : "no package") : m >= 0 ? "under budget" : "over budget"}>
          {m == null ? "—" : (
            <span className="inline-flex items-center gap-1.5">
              {m >= 0 ? <TrendingUp size={20} className="text-emerald-600" /> : <TrendingDown size={20} className="text-rose-600" />}
              <AnimatedNumber value={Math.abs(m)} prefix="€" />
            </span>
          )}
        </Kpi>
        <Kpi label="Blocking issues" sub={res.blockers.length ? "must be resolved" : "none"}>
          <AnimatedNumber value={res.blockers.length} />
        </Kpi>
        <Kpi label="Open questions" sub={res.questions_for_client.length ? "for the client" : "none"}>
          <AnimatedNumber value={res.questions_for_client.length} />
        </Kpi>
      </motion.div>

      <div className="grid gap-5 lg:grid-cols-[1fr_1.15fr]">
        <div className="space-y-5">
          {/* Brief */}
          <motion.section variants={rise} className="card p-5">
            <SectionTitle eyebrow="Step 2" title="Structured brief" />
            <BriefRow label="Confirmed requirements" tone="ok" items={res.brief.confirmed} />
            <BriefRow label="Optional and other requests" tone="opt" items={res.brief.optional_or_other} />
            <BriefRow label="Missing information" tone="miss" items={res.brief.missing} />
            <button onClick={() => setShowEvidence((v) => !v)}
              className="mt-4 flex w-full items-center justify-between rounded-lg bg-canvas px-3 py-2 text-[12.5px] font-medium text-ink-2 hover:text-ink">
              <span className="flex items-center gap-2"><Quote size={13} /> Evidence: the client's words each value came from</span>
              <motion.span animate={{ rotate: showEvidence ? 180 : 0 }}><ChevronDown size={15} /></motion.span>
            </button>
            <AnimatePresence initial={false}>
              {showEvidence && (
                <motion.dl initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden text-[13px]">
                  {Object.entries(res.brief.evidence_quotes).map(([k, v]) => (
                    <div key={k} className="flex gap-3 border-b border-line px-1 py-2 last:border-0">
                      <dt className="w-32 shrink-0 text-ink-3">{k.replace(/_/g, " ")}</dt>
                      <dd className="text-ink">“{v}”</dd>
                    </div>
                  ))}
                  {!Object.keys(res.brief.evidence_quotes).length && <div className="px-1 py-2 text-ink-3">No values extracted.</div>}
                  <div className="px-1 pt-2 text-[11.5px] text-ink-3">Extractor: {res.brief.extractor} · {res.seconds.toFixed(2)} s</div>
                </motion.dl>
              )}
            </AnimatePresence>
          </motion.section>

          {/* Checks */}
          <motion.section variants={rise} className="card p-5">
            <SectionTitle eyebrow="Step 3" title="Salesperson checks" />
            {!checks.length && <p className="text-[13.5px] text-ink-3">Nothing to flag.</p>}
            <motion.ul variants={stagger} className="space-y-2.5">
              {checks.map((c, k) => {
                const sv = SEV[c.kind];
                return (
                  <motion.li key={k} variants={rise} className="flex items-start gap-3">
                    <span className={clsx("mt-0.5 inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-0.5 text-[10.5px] font-bold tracking-wide ring-1 ring-inset", sv.cls)}>
                      <sv.icon size={11} />{c.code}
                    </span>
                    <span className="text-[13.5px] leading-snug text-ink-2">{c.text}</span>
                  </motion.li>
                );
              })}
            </motion.ul>
            {res.audit_violations.length > 0 && (
              <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-[12.5px] text-amber-800 ring-1 ring-amber-200">
                Claude's cover note was rejected by the guardrail and replaced by the template: {res.audit_violations.join("; ")}
              </p>
            )}
            {res.llm_errors.map((e, k) => <p key={k} className="mt-3 text-[12.5px] text-amber-800">{e}</p>)}
          </motion.section>
        </div>

        {/* Draft */}
        <motion.section variants={rise} className="card flex max-h-[720px] flex-col">
          <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
            <div>
              <div className="label">Step 4</div>
              <h3 className="text-[15px] font-semibold">Client draft</h3>
            </div>
            <span className="rounded-full bg-canvas px-2.5 py-1 text-[11.5px] text-ink-3 ring-1 ring-line">
              figures: pricing engine · cover note: {res.cover_source}
            </span>
          </div>
          <div className="draft overflow-y-auto px-5 py-4">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{res.client_draft_markdown}</ReactMarkdown>
          </div>
        </motion.section>
      </div>

      {/* Alternatives */}
      {res.alternatives.length > 0 && (
        <motion.section variants={rise}>
          <SectionTitle eyebrow="Options to offer" title="Alternatives. Each one changes the client's request." />
          <motion.div variants={stagger} className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {res.alternatives.map((a, k) => (
              <motion.article key={k} variants={rise} whileHover={{ y: -4, boxShadow: "0 18px 40px -18px rgba(31,28,87,.28)" }}
                className="card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="label">Option {k + 1}</div>
                    <h4 className="mt-0.5 text-[14.5px] font-semibold leading-snug">{a.title}</h4>
                  </div>
                  <div className="text-right text-[22px] font-semibold tabular-nums tracking-tight">{eur(a.total_eur)}</div>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {a.fits_budget != null && (
                    <span className={clsx("rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset",
                      a.fits_budget ? "bg-emerald-50 text-emerald-800 ring-emerald-200" : "bg-rose-50 text-rose-800 ring-rose-200")}>
                      {a.fits_budget ? "within budget" : "above budget"}
                    </span>
                  )}
                  {a.changes_a_must_have && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800 ring-1 ring-inset ring-amber-200">
                      <TriangleAlert size={10} /> changes the request
                    </span>
                  )}
                </div>
                <ul className="mt-3 space-y-1.5 border-t border-line pt-3 text-[13px] text-ink-2">
                  {a.trade_offs.map((t, i) => <li key={i} className="flex gap-2"><span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-ink-3" />{t}</li>)}
                </ul>
              </motion.article>
            ))}
          </motion.div>
        </motion.section>
      )}

      {/* Approval */}
      <motion.section variants={rise} className={clsx("card overflow-hidden p-5 transition-colors", approved && "ring-2 ring-emerald-300")}>
        <SectionTitle eyebrow="Step 5" title="Salesperson approval" />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <label className="flex cursor-pointer items-start gap-3 text-[14px] text-ink-2">
            <button type="button" role="checkbox" aria-checked={ack} onClick={() => { setAck(!ack); if (ack) setApproved(false); }}
              className={clsx("mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md ring-1 transition-colors", ack ? "bg-brand-600 ring-brand-600" : "bg-white ring-ink-3/50")}>
              <AnimatePresence>{ack && <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}><Check size={13} strokeWidth={3.5} className="text-white" /></motion.span>}</AnimatePresence>
            </button>
            <span onClick={() => { setAck(!ack); if (ack) setApproved(false); }}>{ackText}.</span>
          </label>
          <motion.button whileHover={ack ? { scale: 1.02 } : {}} whileTap={ack ? { scale: 0.97 } : {}} disabled={!ack || approved}
            onClick={() => setApproved(true)}
            className={clsx("inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-semibold transition-colors",
              approved ? "bg-emerald-600 text-white" : "bg-ink text-white disabled:bg-line disabled:text-ink-3")}>
            <ClipboardCheck size={16} />{approved ? "Approved" : "Approve draft"}
          </motion.button>
        </div>
        <AnimatePresence>
          {approved && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="mt-4 flex flex-wrap items-center gap-4 rounded-xl bg-emerald-50 px-4 py-3.5 ring-1 ring-emerald-200">
                <svg width="34" height="34" viewBox="0 0 34 34" className="shrink-0">
                  <motion.circle cx="17" cy="17" r="15" fill="none" stroke="#059669" strokeWidth="2.5"
                    initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.5 }} />
                  <motion.path d="M10 17.5l4.6 4.6L24 12.5" fill="none" stroke="#059669" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round"
                    initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.35, delay: 0.4 }} />
                </svg>
                <p className="min-w-0 flex-1 text-[14px] text-emerald-900">
                  <span className="font-semibold">Approved by you.</span> Nothing has been sent or booked. Send it yourself after the availability check.
                </p>
                <div className="flex gap-2">
                  <button onClick={onCopy} className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-[13px] font-medium text-ink ring-1 ring-line hover:ring-ink-3">
                    {copied ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}{copied ? "Copied" : "Copy text"}
                  </button>
                  <button onClick={download} className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-[13px] font-medium text-ink ring-1 ring-line hover:ring-ink-3">
                    <Download size={14} />Download .md
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.section>
    </motion.div>
  );
}

function Kpi({ label, sub, children }: { label: string; sub: string; children: React.ReactNode }) {
  return (
    <motion.div variants={rise} whileHover={{ y: -2 }} className="card px-4 py-3.5">
      <div className="label">{label}</div>
      <div className="mt-1 text-[26px] font-semibold tabular-nums tracking-tight text-ink">{children}</div>
      <div className="mt-0.5 truncate text-[12.5px] text-ink-3">{sub}</div>
    </motion.div>
  );
}

function BriefRow({ label, tone, items }: { label: string; tone: "ok" | "opt" | "miss"; items: string[] }) {
  return (
    <div className="mt-3 first:mt-0">
      <div className="mb-1.5 text-[12px] font-medium text-ink-3">{label}</div>
      {items.length ? (
        <motion.div variants={stagger} className="flex flex-wrap gap-1.5">
          {items.map((x) => <Chip key={x} tone={tone}>{x}</Chip>)}
        </motion.div>
      ) : <span className="text-[13px] text-ink-3">None</span>}
    </div>
  );
}
