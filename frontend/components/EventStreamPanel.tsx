"use client";

import { Card, CardContent, CardHeader, CardTitle } from "./Card";
import { Badge, VerdictBadge } from "./Badge";
import type { SentinelEvent } from "@/lib/types";
import Link from "next/link";

const EVENT_TYPE_LABEL: Record<string, string> = {
  prompt: "Prompt",
  tool_call: "Tool call",
  api_request: "API request",
  output: "Output",
};

const VERDICT_BORDER: Record<string, string> = {
  allow: "border-l-success",
  wait: "border-l-warning",
  block: "border-l-danger",
  pending: "border-l-border",
};

export function EventStreamPanel({
  events,
  title = "Live event stream",
  emptyLabel = "No events yet. Send a message to see the pipeline light up.",
}: {
  events: SentinelEvent[];
  title?: string;
  emptyLabel?: string;
}) {
  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-1.5 max-h-[70vh] scanlines">
        {events.length === 0 && <div className="text-sm text-muted-foreground">{emptyLabel}</div>}
        {events.map((e) => (
          <div
            key={e.id}
            className={`border-l-[3px] bg-surface-hover/40 pl-3 pr-2.5 py-2 text-sm ${
              VERDICT_BORDER[e.verdict?.decision ?? "pending"]
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <Badge tone="default">{EVENT_TYPE_LABEL[e.event_type] ?? e.event_type}</Badge>
                <span className="text-xs text-muted-foreground">{e.source}</span>
              </div>
              <VerdictBadge decision={e.verdict?.decision} pending={!e.verdict} />
            </div>
            <div className="mono text-xs text-muted-foreground truncate">
              {JSON.stringify(e.payload).slice(0, 140)}
            </div>
            {e.detections.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {e.detections.map((d) => (
                  <Badge key={d.detector_name} tone={d.triggered ? "danger" : "default"} className="text-[10px]">
                    {d.detector_name}: {d.score.toFixed(2)}
                  </Badge>
                ))}
              </div>
            )}
            {e.verdict && (
              <div className="mt-1.5 flex items-center justify-between text-xs">
                <span className="mono text-muted-foreground">
                  R {e.verdict.risk_score.toFixed(2)}, driven by {e.verdict.dominant_factor}
                </span>
                {e.verdict.id && (
                  <Link href={`/reports/${e.verdict.id}`} className="text-primary hover:underline">
                    Full report
                  </Link>
                )}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
