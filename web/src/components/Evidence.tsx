import { AnimatePresence, motion } from "framer-motion";
import { Check, Loader2, Play, X } from "lucide-react";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { api, eur } from "../api";
import type { BaselineRow, Case, EvalResult } from "../types";
import { SectionTitle, STATUS, rise, stagger } from "./ui";

const TILES = [
  { label: "Designed tests", value: "16 / 16", sub: "prototype, re-run live below" },
  { label: "Single-prompt baseline", value: "12 / 16", sub: "2 partial · 2 fail" },
  { label: "Forbidden promises", value: "4 → 0", sub: "baseline → prototype" },
  { label: "Blind set 1, first run", value: "5 / 10", sub: "every miss was extraction" },
  { label: "Blind set 2, first run", value: "7 / 10", sub: "6 / 10 strictly" },
];

function Judgement({ text }: { text: string }) {
  const tone = text.startsWith("PASS") ? "bg-emerald-50 text-emerald-800 ring-emerald-200"
    : text.startsWith("PARTIAL") ? "bg-amber-50 text-amber-800 ring-amber-200" : "bg-rose-50 text-rose-800 ring-rose-200";
  return <span className={clsx("whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset", tone)}>{text}</span>;
}

export default function Evidence({ cases }: { cases: Case[] }) {
  const [baseline, setBaseline] = useState<BaselineRow[]>([]);
  const [ev, setEv] = useState<EvalResult | null>(null);
  const [running, setRunning] = useState(false);
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => { api.baseline().then(setBaseline).catch(() => {}); }, []);

  async function runAll() {
    setRunning(true); setEv(null);
    const [r] = await Promise.all([api.runEval(), new Promise((res) => setTimeout(res, 500))]);
    setEv(r); setRunning(false);
  }
  const proto = Object.fromEntries((ev?.rows ?? []).filter((r) => r.set === "Designed").map((r) => [r.id, r]));
  const hovered = ev?.rows.find((r) => r.set + r.id === hover);

  return (
    <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-6">
      <motion.header variants={rise}>
        <div className="label mb-2">Test evidence</div>
        <h1 className="font-display text-[44px] leading-[1.05] tracking-tight">Does it work? <em className="text-brand-600">Measured</em>, not claimed.</h1>
        <p className="mt-2 max-w-3xl text-[15px] text-ink-2">
          The same enquiries went through a plain single-prompt baseline and through the prototype. Two more test sets
          were written by independent agents that never saw the code.
        </p>
      </motion.header>

      <motion.div variants={stagger} className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {TILES.map((t) => (
          <motion.div key={t.label} variants={rise} whileHover={{ y: -2 }} className="card px-4 py-3.5">
            <div className="label">{t.label}</div>
            <div className="mt-1 text-[26px] font-semibold tabular-nums tracking-tight">{t.value}</div>
            <div className="mt-0.5 text-[12.5px] text-ink-3">{t.sub}</div>
          </motion.div>
        ))}
      </motion.div>

      <motion.p variants={rise} className="max-w-4xl text-[13.5px] leading-relaxed text-ink-2">
        The baseline got every total right. Its failures were promises and scope: “we can confirm this option now”,
        allergen catering from outside the catalogue, and invented “illustrative” packages when the headcount was
        missing. On the blind sets every prototype miss was in reading the enquiry, never in pricing. After those
        gaps were fixed both blind sets pass, but they are then no longer blind.
      </motion.p>

      {/* live run */}
      <motion.section variants={rise} className="card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line bg-grid px-5 py-4">
          <div>
            <div className="label">Live</div>
            <h3 className="text-[15px] font-semibold">Re-run all 36 tests on this machine</h3>
            <p className="text-[13px] text-ink-3">Deterministic rules mode. Each square is one enquiry checked against its expected result.</p>
          </div>
          <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={runAll} disabled={running}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-[14px] font-semibold text-white shadow-[0_8px_20px_-8px_rgba(74,67,196,.7)] hover:bg-brand-700 disabled:opacity-60">
            {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={15} fill="currentColor" />}
            {running ? "Running…" : ev ? "Run again" : "Run all tests"}
          </motion.button>
        </div>
        <div className="px-5 py-5">
          {!ev && !running && <p className="text-[13.5px] text-ink-3">Press the button to run the three test sets.</p>}
          {running && <div className="h-24 animate-pulse rounded-xl bg-canvas" />}
          {ev && (
            <div className="space-y-4">
              {Object.entries(ev.sets).map(([name, s], si) => (
                <div key={name} className="flex flex-wrap items-center gap-4">
                  <div className="w-36">
                    <div className="text-[13px] font-semibold">{name}</div>
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 + si * 0.25 }}
                      className="text-[22px] font-semibold tabular-nums tracking-tight">{s.passed} / {s.total}</motion.div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {ev.rows.filter((r) => r.set === name).map((r, i) => (
                      <motion.button key={r.id} onMouseEnter={() => setHover(r.set + r.id)} onMouseLeave={() => setHover(null)}
                        initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                        transition={{ type: "spring", stiffness: 500, damping: 22, delay: si * 0.25 + i * 0.03 }}
                        whileHover={{ scale: 1.18 }}
                        className={clsx("grid h-8 w-8 place-items-center rounded-lg text-white", r.pass ? "bg-emerald-500" : "bg-rose-500")}>
                        {r.pass ? <Check size={15} strokeWidth={3} /> : <X size={15} strokeWidth={3} />}
                      </motion.button>
                    ))}
                  </div>
                </div>
              ))}
              <div className="h-10">
                <AnimatePresence mode="wait">
                  {hovered && (
                    <motion.div key={hover} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      className="inline-flex flex-wrap items-center gap-2 rounded-lg bg-canvas px-3 py-2 text-[13px] ring-1 ring-line">
                      <span className="font-semibold">{hovered.id}</span><span className="text-ink-3">{hovered.type}</span>
                      <span className={clsx("h-2 w-2 rounded-full", STATUS[hovered.status].dot)} />{STATUS[hovered.status].short}
                      <span className="tabular-nums text-ink-2">{eur(hovered.total)}</span>
                      {!hovered.pass && <span className="text-rose-700">{hovered.fails.join("; ")}</span>}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          )}
        </div>
      </motion.section>

      {/* table */}
      <motion.section variants={rise} className="card overflow-hidden">
        <div className="px-5 pt-4"><SectionTitle eyebrow="16 designed cases" title="Baseline vs prototype, case by case" /></div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead className="bg-canvas text-[11px] uppercase tracking-wider text-ink-3">
              <tr>{["ID", "Enquiry", "Single-prompt baseline", "Baseline", "Prototype"].map((h) => <th key={h} className="px-4 py-2.5 font-semibold">{h}</th>)}</tr>
            </thead>
            <tbody>
              {cases.map((c) => {
                const b = baseline.find((x) => x.id === c.id); const p = proto[c.id];
                return (
                  <tr key={c.id} className="border-t border-line align-top transition-colors hover:bg-brand-50/40">
                    <td className="px-4 py-3 font-semibold text-ink-2">{c.id}</td>
                    <td className="max-w-[340px] px-4 py-3 text-ink">{c.enquiry}<div className="mt-1 text-[12px] text-ink-3">Expected: {c.expected}</div></td>
                    <td className="max-w-[320px] px-4 py-3 text-ink-2">{b?.baseline.replace(/\*\*/g, "") ?? "—"}</td>
                    <td className="px-4 py-3">{b ? <Judgement text={b.judgement} /> : "—"}</td>
                    <td className="px-4 py-3">{p ? <Judgement text={p.pass ? "PASS" : "FAIL"} /> : <span className="text-[12px] text-ink-3">run tests</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </motion.section>
    </motion.div>
  );
}
