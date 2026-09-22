"use client";

import { useEffect, useState } from "react";

/**
 * Visual gauge for a 0-1 risk score `R`, with the three threshold bands
 * (allow/wait/block) shown as colored zones on an analog dial rather than
 * a linear progress bar — this is the one instrument-like, animated
 * element in the app; everything around it stays quiet.
 */

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end = polarToCartesian(cx, cy, r, endAngle);
  const largeArcFlag = Math.abs(startAngle - endAngle) <= 180 ? 0 : 1;
  const sweepFlag = startAngle > endAngle ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} ${sweepFlag} ${end.x} ${end.y}`;
}

const angleForScore = (s: number) => 180 - Math.min(Math.max(s, 0), 1) * 180;

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
  const clamped = Math.min(Math.max(score, 0), 1);
  const [needleScore, setNeedleScore] = useState(0);

  // Sweep in from zero on mount (and re-sweep whenever a live update
  // changes the score) instead of snapping straight to the value.
  useEffect(() => {
    const t = setTimeout(() => setNeedleScore(clamped), 60);
    return () => clearTimeout(t);
  }, [clamped]);

  let band: "success" | "warning" | "danger" = "success";
  if (clamped >= blockThreshold) band = "danger";
  else if (clamped >= waitThreshold) band = "warning";

  const dims =
    size === "sm"
      ? { w: 200, h: 118, cx: 100, cy: 100, r: 72, stroke: 11, needle: 54, num: "text-xl" }
      : { w: 260, h: 148, cx: 130, cy: 128, r: 96, stroke: 14, needle: 74, num: "text-3xl" };

  const { w, h, cx, cy, r, stroke, needle, num } = dims;
  const needleAngle = angleForScore(needleScore);
  const rotationDeg = needleScore * 180; // 0deg = resting at score 0 (pointing left)

  return (
    <div className="w-full flex flex-col items-center">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-[280px]">
        <path
          d={arcPath(cx, cy, r, 180, angleForScore(waitThreshold))}
          stroke="hsl(var(--success))"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          opacity={0.85}
        />
        <path
          d={arcPath(cx, cy, r, angleForScore(waitThreshold), angleForScore(blockThreshold))}
          stroke="hsl(var(--warning))"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          opacity={0.85}
        />
        <path
          d={arcPath(cx, cy, r, angleForScore(blockThreshold), 0)}
          stroke="hsl(var(--danger))"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          opacity={0.85}
        />

        <g style={{ transformOrigin: `${cx}px ${cy}px`, transition: "transform 700ms cubic-bezier(0.22, 1, 0.36, 1)" }}
           transform={`rotate(${rotationDeg})`}>
          <line
            x1={cx}
            y1={cy}
            x2={cx - needle}
            y2={cy}
            stroke="hsl(var(--foreground))"
            strokeWidth={2.5}
            strokeLinecap="round"
          />
        </g>
        <circle cx={cx} cy={cy} r={6} fill="hsl(var(--foreground))" />
        <circle cx={cx} cy={cy} r={2.5} fill="hsl(var(--surface))" />

        <text x={polarToCartesian(cx, cy, r + 18, 180).x} y={polarToCartesian(cx, cy, r + 18, 180).y}
              textAnchor="start" fontSize={10} fill="hsl(var(--muted-foreground))" className="mono">0</text>
        <text x={polarToCartesian(cx, cy, r + 18, 0).x} y={polarToCartesian(cx, cy, r + 18, 0).y}
              textAnchor="end" fontSize={10} fill="hsl(var(--muted-foreground))" className="mono">1</text>
      </svg>

      <div className="-mt-2 flex flex-col items-center">
        <div
          className={`display font-bold ${num} leading-none`}
          style={{
            color:
              band === "success"
                ? "hsl(var(--success))"
                : band === "warning"
                ? "hsl(var(--warning))"
                : "hsl(var(--danger))",
          }}
        >
          {clamped.toFixed(2)}
        </div>
        <div className="text-[11px] text-muted-foreground mono mt-0.5">risk score R</div>
      </div>
    </div>
  );
}
