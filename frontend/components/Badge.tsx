import { HTMLAttributes } from "react";
import type { Decision } from "@/lib/types";

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

export function Badge({
  className,
  tone = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "default" | "success" | "warning" | "danger" | "primary" }) {
  const toneClasses: Record<string, string> = {
    default: "bg-surface-hover text-muted-foreground border-border",
    success: "bg-success/10 text-success border-success/30",
    warning: "bg-warning/10 text-warning border-warning/30",
    danger: "bg-danger/10 text-danger border-danger/30",
    primary: "bg-primary/10 text-primary border-primary/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}

const DECISION_LABEL: Record<Decision, string> = {
  allow: "Allow",
  wait: "Wait",
  block: "Block",
};

const DECISION_TONE: Record<Decision, "success" | "warning" | "danger"> = {
  allow: "success",
  wait: "warning",
  block: "danger",
};

export function VerdictBadge({ decision, pending }: { decision?: Decision; pending?: boolean }) {
  if (pending || !decision) {
    return <Badge tone="default">Pending…</Badge>;
  }
  return <Badge tone={DECISION_TONE[decision]}>{DECISION_LABEL[decision]}</Badge>;
}
