import type { Analysis, BaselineRow, Case, EvalResult, Health } from "./types";

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? r.statusText);
  return r.json();
}
export const api = {
  health: () => j<Health>("/api/health"),
  cases: () => j<Case[]>("/api/cases"),
  baseline: () => j<BaselineRow[]>("/api/baseline"),
  analyse: (enquiry: string, use_llm?: boolean) =>
    j<Analysis>("/api/analyse", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enquiry, use_llm }) }),
  runEval: () => j<EvalResult>("/api/eval", { method: "POST" }),
};

export const eur = (n: number | null | undefined) =>
  n == null ? "—" : "€" + Math.round(n).toLocaleString("en-US").replace(/,/g, " ");
