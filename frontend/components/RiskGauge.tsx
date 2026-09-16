"use client";

/**
 * Visual gauge for a 0-1 risk score `R`, with the three threshold bands
 * (allow/wait/block) shown as colored zones (build spec §5.3).
 */
export function RiskGauge({
  score,
  waitThreshold = 0.45,
  blockThreshold = 0.75,
  size = "md",
}: {
  score: number;
  waitThreshold?: number;
  blockThreshold?: number;
  size?: "sm" | "md";
}) {
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);
  const height = size === "sm" ? "h-2" : "h-3";

  let fillColor = "bg-success";
  if (score >= blockThreshold) fillColor = "bg-danger";
  else if (score >= waitThreshold) fillColor = "bg-warning";

  return (
    <div className="w-full">
      <div className={`relative w-full ${height} rounded-full bg-surface-hover overflow-hidden`}>
        <div
          className="absolute inset-y-0 left-0 rounded-full pointer-events-none border-r-2 border-dashed border-warning/60"
          style={{ width: `${waitThreshold * 100}%` }}
        />
        <div
          className="absolute inset-y-0 left-0 rounded-full pointer-events-none border-r-2 border-dashed border-danger/60"
          style={{ width: `${blockThreshold * 100}%` }}
        />
        <div
          className={`h-full rounded-full ${fillColor} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between mt-1 text-[10px] text-muted-foreground mono">
        <span>0.0</span>
        <span>R = {score.toFixed(2)}</span>
        <span>1.0</span>
      </div>
    </div>
  );
}
