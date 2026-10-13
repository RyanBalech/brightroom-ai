import { AnimatePresence, motion } from "framer-motion";
import { BarChart3, Compass, Cpu, PenSquare, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { api } from "./api";
import type { Case, Health } from "./types";
import Assistant from "./components/Assistant";
import Evidence from "./components/Evidence";
import How from "./components/How";

const NAV = [
  { id: "assistant", label: "Proposal assistant", icon: PenSquare },
  { id: "evidence", label: "Test evidence", icon: BarChart3 },
  { id: "how", label: "How it works", icon: Compass },
] as const;
type Page = (typeof NAV)[number]["id"];

export default function App() {
  const [page, setPage] = useState<Page>(() => (["assistant", "evidence", "how"].includes(location.hash.slice(1)) ? (location.hash.slice(1) as Page) : "assistant"));
  const [cases, setCases] = useState<Case[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setDown(true));
    api.cases().then(setCases).catch(() => setDown(true));
  }, []);
  useEffect(() => { history.replaceState(null, "", location.pathname + location.search + "#" + page); }, [page]);

  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 flex-col border-r border-line bg-white/70 px-4 py-5 md:flex">
        <div className="flex items-center gap-2.5 px-2">
          <motion.div initial={{ rotate: -90, scale: 0.6 }} animate={{ rotate: 0, scale: 1 }} transition={{ type: "spring", stiffness: 200, damping: 14 }}
            className="grid h-9 w-9 place-items-center rounded-xl bg-brand-900 shadow-[0_6px_16px_-6px_rgba(31,28,87,.7)]">
            <svg width="20" height="20" viewBox="0 0 20 20"><circle cx="10" cy="10" r="7" fill="none" stroke="#fff" strokeWidth="2" /><path d="M10 3a7 7 0 0 1 0 14z" fill="#fbbf24" /></svg>
          </motion.div>
          <div>
            <div className="text-[15px] font-semibold leading-none tracking-tight">BrightRoom</div>
            <div className="mt-1 text-[11.5px] text-ink-3">Workshop studio · Sales</div>
          </div>
        </div>
        <nav className="mt-7 space-y-1">
          {NAV.map((n) => (
            <button key={n.id} onClick={() => setPage(n.id)}
              className={clsx("relative flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-[13.5px] font-medium transition-colors", page === n.id ? "text-brand-700" : "text-ink-2 hover:text-ink")}>
              {page === n.id && <motion.span layoutId="nav" transition={{ type: "spring", stiffness: 420, damping: 34 }} className="absolute inset-0 rounded-xl bg-brand-50 ring-1 ring-brand-100" />}
              <n.icon size={16} className="relative" /><span className="relative">{n.label}</span>
            </button>
          ))}
        </nav>
        <div className="mt-auto space-y-3">
          <div className="rounded-xl bg-canvas p-3 ring-1 ring-line">
            <div className="flex items-center gap-2 text-[12px] font-semibold text-ink">
              {health?.llm_available ? <Sparkles size={13} className="text-brand-600" /> : <Cpu size={13} className="text-ink-3" />}
              {health?.llm_available ? "Claude mode" : "Rules mode"}
              <span className="relative ml-auto flex h-2 w-2">
                <span className={clsx("absolute inline-flex h-full w-full animate-ping rounded-full opacity-60", down ? "bg-rose-400" : "bg-emerald-400")} />
                <span className={clsx("relative inline-flex h-2 w-2 rounded-full", down ? "bg-rose-500" : "bg-emerald-500")} />
              </span>
            </div>
            <div className="mt-1 text-[11.5px] leading-snug text-ink-3">
              {down ? "Engine not reachable. Start it with: python api.py" : health?.llm_available ? health.model : "Offline and deterministic. Prices always come from code."}
            </div>
          </div>
          <div className="px-2 text-[11px] text-ink-3">HEC MSc DSAIB · Case 02<br />Fictional teaching material</div>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-[1180px] px-5 py-8 md:px-10">
          <div className="mb-5 flex gap-1 md:hidden">
            {NAV.map((n) => <button key={n.id} onClick={() => setPage(n.id)} className={clsx("rounded-lg px-3 py-1.5 text-[13px] font-medium", page === n.id ? "bg-brand-600 text-white" : "bg-white text-ink-2 ring-1 ring-line")}>{n.label}</button>)}
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={page} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.22 }}>
              {page === "assistant" && <Assistant cases={cases} health={health} />}
              {page === "evidence" && <Evidence cases={cases} />}
              {page === "how" && <How />}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
