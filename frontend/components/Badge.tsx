import { HTMLAttributes } from "react";
import type { Decision } from "@/lib/types";

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

const DOT_CLASSES: Record<string, string> = {
  default: "bg-muted-foreground",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  primary: "bg-primary",
};

const TEXT_CLASSES: Record<string, string> = {
  default: "text-muted-foreground border-border",
  success: "text-success border-success/35",
  warning: "text-warning border-warning/35",
  danger: "text-danger border-danger/35",
  primary: "text-primary border-primary/35",
};

export function Badge({
  className,
  tone = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "default" | "success" | "warning" | "danger" | "primary" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border bg-surface px-1.5 py-0.5 text-xs font-medium",
        TEXT_CLASSES[tone],
        className
      )}
    >
      <span className={cn("inline-block w-1.5 h-1.5 rounded-full shrink-0", DOT_CLASSES[tone])} aria-hidden />
      <span {...props} />
    </span>
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
    return <Badge tone="default">Pending</Badge>;
  }
  return <Badge tone={DECISION_TONE[decision]}>{DECISION_LABEL[decision]}</Badge>;
}
