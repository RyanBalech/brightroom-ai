import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { AlertTriangle, CheckCircle2, HelpCircle, OctagonX, type LucideIcon } from "lucide-react";
import { useEffect } from "react";
import clsx from "clsx";
import type { Status } from "../types";

export const STATUS: Record<Status, {
  icon: LucideIcon; title: string; desc: string; ring: string; bg: string; fg: string; dot: string; short: string;
}> = {
  READY_FOR_REVIEW: {
    icon: CheckCircle2, short: "Feasible", title: "Feasible — ready for your review",
    desc: "Every requirement is met from the catalogue.",
    ring: "ring-emerald-200", bg: "from-emerald-50 to-white", fg: "text-emerald-700", dot: "bg-emerald-500",
  },
  PROVISIONAL: {
    icon: AlertTriangle, short: "Provisional", title: "Provisional — check the labelled assumptions",
    desc: "Feasible, but some details were not stated. Confirm the assumptions or ask the questions.",
    ring: "ring-amber-200", bg: "from-amber-50 to-white", fg: "text-amber-700", dot: "bg-amber-400",
  },
  INFEASIBLE: {
    icon: OctagonX, short: "Infeasible", title: "Cannot meet the brief as stated — do not send as-is",
    desc: "At least one requirement cannot be met. Offer the alternatives; each one names its trade-off.",
    ring: "ring-rose-200", bg: "from-rose-50 to-white", fg: "text-rose-700", dot: "bg-rose-500",
  },
  NEEDS_CLARIFICATION: {
    icon: HelpCircle, short: "Clarify", title: "Clarification needed — no prices yet",
    desc: "Key information is missing; quoting now would mean inventing numbers. Send the questions.",
    ring: "ring-brand-100", bg: "from-brand-50 to-white", fg: "text-brand-700", dot: "bg-brand-500",
  },
};

export function AnimatedNumber({ value, prefix = "", className }: { value: number; prefix?: string; className?: string }) {
  const mv = useMotionValue(0);
  const text = useTransform(mv, (v) => prefix + Math.round(v).toLocaleString("en-US").replace(/,/g, " "));
  useEffect(() => {
    const c = animate(mv, value, { duration: 0.9, ease: [0.16, 1, 0.3, 1] });
    return c.stop;
  }, [value, mv]);
  return <motion.span className={className}>{text}</motion.span>;
}

export function Chip({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "ok" | "opt" | "miss" | "neutral" }) {
  return (
    <motion.span
      variants={{ hidden: { opacity: 0, y: 6, scale: 0.96 }, show: { opacity: 1, y: 0, scale: 1 } }}
      className={clsx(
        "inline-flex items-center rounded-full px-3 py-1 text-[12.5px] font-medium ring-1 ring-inset",
        tone === "ok" && "bg-emerald-50 text-emerald-800 ring-emerald-200",
        tone === "opt" && "bg-brand-50 text-brand-700 ring-brand-100",
        tone === "miss" && "bg-amber-50 text-amber-800 ring-amber-200",
        tone === "neutral" && "bg-canvas text-ink-2 ring-line",
      )}
    >
      {children}
    </motion.span>
  );
}

export const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.045 } } };

export const rise = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 260, damping: 26 } },
};

export function SectionTitle({ eyebrow, title, right }: { eyebrow?: string; title: string; right?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-4">
      <div>
        {eyebrow && <div className="label mb-1">{eyebrow}</div>}
        <h3 className="text-[15px] font-semibold text-ink">{title}</h3>
      </div>
      {right}
    </div>
  );
}
