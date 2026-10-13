export type Status = "READY_FOR_REVIEW" | "PROVISIONAL" | "INFEASIBLE" | "NEEDS_CLARIFICATION";

export interface LineItem { id: string; name: string; unit_price_eur: number; qty: number; amount_eur: number }
export interface Pkg { headcount: number; venue: string; items: LineItem[]; total_eur: number }
export interface Alternative {
  title: string; total_eur: number; fits_budget: boolean | null; trade_offs: string[];
  changes_a_must_have: boolean; packages: Pkg[];
}
export interface Issue { code: string; severity: "blocker" | "warning" | "info"; message: string }
export interface Analysis {
  status: Status; status_label: string;
  brief: { confirmed: string[]; optional_or_other: string[]; missing: string[]; evidence_quotes: Record<string, string>; extractor: string };
  package: Pkg | null; budget_eur: number | null; budget_margin_eur: number | null;
  blockers: string[]; warnings: string[]; assumptions: string[]; questions_for_client: string[]; notes: string[];
  alternatives: Alternative[]; venue_name: string | null; headcount: number | null;
  client_draft_markdown: string; cover_source: string; audit_violations: string[]; llm_errors: string[];
  seconds: number; issues: Issue[];
}
export interface Case { id: string; type: string; source: string; enquiry: string; expected: string }
export interface EvalRow { set: string; id: string; type: string; status: Status; total: number | null; pass: boolean; fails: string[] }
export interface EvalResult { sets: Record<string, { passed: number; total: number }>; rows: EvalRow[] }
export interface BaselineRow { id: string; expected: string; baseline: string; judgement: string }
export interface Health { ok: boolean; llm_available: boolean; model: string }
