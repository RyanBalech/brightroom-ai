import { motion } from "framer-motion";
import { ArrowRight, Bot, Calculator, GitBranch, PenLine, Plug, UserCheck } from "lucide-react";
import clsx from "clsx";
import { STATUS, rise, stagger } from "./ui";
import type { Status } from "../types";

const FLOW = [
  { icon: Bot, who: "GenAI", title: "Read", text: "Enquiry becomes a brief. Every number must quote the client's words and is cross-checked by rules.", tone: "ai" },
  { icon: Calculator, who: "Code", title: "Decide", text: "Venue, capacity, access, 4-hour limit, prices, totals, budget and status.", tone: "code" },
  { icon: GitBranch, who: "Code", title: "Alternatives", text: "Re-priced variants. Each one lists exactly what changes from the request.", tone: "code" },
  { icon: PenLine, who: "GenAI", title: "Write", text: "A short cover note, audited for invented prices and promises.", tone: "ai" },
  { icon: UserCheck, who: "Human", title: "Approve", text: "The salesperson reviews the flags, approves, checks availability and sends.", tone: "human" },
];
const TONE: Record<string, string> = {
  ai: "bg-brand-50 ring-brand-100 text-brand-700",
  code: "bg-white ring-line text-ink-2",
  human: "bg-emerald-50 ring-emerald-200 text-emerald-700",
};
const RULES: { s: Status; when: string; then: string }[] = [
  { s: "NEEDS_CLARIFICATION", when: "No headcount", then: "Questions only. Any price would be invented." },
  { s: "PROVISIONAL", when: "A gap with a safe default: no budget, “about 15”, “with food”, no duration, access unknown with the stairs-only Studio", then: "Provisional draft with every assumption labelled." },
  { s: "INFEASIBLE", when: "A stated need can't be met: over 24 people, over 4 hours, over budget, facilitator over 2 hours, allergen guarantee, must-have outside the catalogue", then: "No package shown as valid. Alternatives with their trade-offs." },
  { s: "READY_FOR_REVIEW", when: "Everything stated and satisfiable", then: "Itemised package, ready for review." },
];
const TOOLS = [
  ["analyse_enquiry", "Enquiry in; brief, status, package, alternatives and questions out"],
  ["price_brief", "Price a brief that Claude extracted itself"],
  ["check_draft", "Audit any message for invented prices or promises"],
  ["get_catalogue", "The approved catalogue"],
];

export default function How() {
  return (
    <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-7">
      <motion.header variants={rise}>
        <div className="label mb-2">How it works</div>
        <h1 className="font-display text-[44px] leading-[1.05] tracking-tight">AI for the <em className="text-brand-600">language</em>. Code for the numbers.</h1>
        <p className="mt-2 max-w-3xl text-[15px] text-ink-2">One fixed workflow, not an autonomous agent. The risk here is a confident error, so everything that must be exact is computed, and a person approves every draft.</p>
      </motion.header>

      <motion.div variants={stagger} className="grid gap-3 lg:grid-cols-[repeat(5,1fr)]">
        {FLOW.map((f, i) => (
          <motion.div key={f.title} variants={rise} whileHover={{ y: -3 }} className={clsx("relative rounded-2xl p-4 ring-1", TONE[f.tone])}>
            <div className="flex items-center justify-between">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-white shadow-sm ring-1 ring-line"><f.icon size={18} /></span>
              <span className="text-[10.5px] font-bold uppercase tracking-widest opacity-80">{f.who}</span>
            </div>
            <h3 className="mt-3 text-[15px] font-semibold text-ink">{i + 1}. {f.title}</h3>
            <p className="mt-1 text-[13px] leading-snug text-ink-2">{f.text}</p>
            {i < FLOW.length - 1 && (
              <motion.span initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 + i * 0.12 }}
                className="absolute -right-[13px] top-1/2 z-10 hidden h-6 w-6 -translate-y-1/2 place-items-center rounded-full bg-white text-ink-3 shadow ring-1 ring-line lg:grid">
                <ArrowRight size={13} />
              </motion.span>
            )}
          </motion.div>
        ))}
      </motion.div>

      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <motion.section variants={rise} className="card p-5">
          <div className="label mb-1">Policy</div>
          <h3 className="mb-3 text-[15px] font-semibold">When does it ask instead of quoting?</h3>
          <div className="space-y-3">
            {RULES.map((r) => {
              const S = STATUS[r.s];
              return (
                <div key={r.s} className="flex gap-3">
                  <span className={clsx("mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br ring-1", S.bg, S.ring, S.fg)}><S.icon size={16} /></span>
                  <div className="text-[13.5px] leading-snug"><span className="font-semibold text-ink">{S.short}.</span> <span className="text-ink-2">{r.when}.</span><div className="text-ink-3">{r.then}</div></div>
                </div>
              );
            })}
          </div>
          <p className="mt-4 rounded-xl bg-canvas px-3.5 py-3 text-[13px] text-ink-2 ring-1 ring-line">
            <span className="font-semibold text-ink">It never</span> confirms a booking or a date, offers a discount, adds a service outside the catalogue, or silently drops a must-have to make the numbers work.
          </p>
        </motion.section>

        <motion.section variants={rise} className="card overflow-hidden">
          <div className="bg-brand-900 px-5 py-4 text-white">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-widest text-white/60"><Plug size={13} /> MCP server</div>
            <h3 className="mt-1 text-[15px] font-semibold">Use the same engine from Claude</h3>
            <code className="mt-2 block rounded-lg bg-white/10 px-3 py-2 font-mono text-[12.5px] text-white/90">python -m brightroom.mcp_server</code>
          </div>
          <ul className="divide-y divide-line">
            {TOOLS.map(([n, d]) => (
              <li key={n} className="flex gap-3 px-5 py-3 text-[13px]">
                <code className="w-36 shrink-0 font-mono text-[12.5px] font-semibold text-brand-700">{n}</code><span className="text-ink-2">{d}</span>
              </li>
            ))}
          </ul>
          <p className="border-t border-line px-5 py-3 text-[12.5px] text-ink-3">Claude holds the conversation. The tools guarantee every number. All tools are read-only.</p>
        </motion.section>
      </div>
    </motion.div>
  );
}
