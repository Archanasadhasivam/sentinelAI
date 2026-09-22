"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useEventStream } from "@/lib/ws";
import type { SentinelEvent, WSMessage } from "@/lib/types";
import { Card, CardContent } from "@/components/Card";
import { Badge, VerdictBadge } from "@/components/Badge";

export default function MonitorPage() {
  const [events, setEvents] = useState<SentinelEvent[]>([]);
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [decisionFilter, setDecisionFilter] = useState("");

  async function reload() {
    const params: Record<string, string> = { limit: "100" };
    if (eventTypeFilter) params.event_type = eventTypeFilter;
    if (decisionFilter) params.decision = decisionFilter;
    const res = await api.listEvents(params);
    setEvents(res.events);
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventTypeFilter, decisionFilter]);

  useEventStream((msg: WSMessage) => {
    if (msg.kind === "event_created") {
      setEvents((prev) => [
        {
          id: msg.data.id,
          session_id: msg.data.session_id,
          event_type: msg.data.event_type,
          source: msg.data.source,
          payload: msg.data.payload,
          status: msg.data.status,
          created_at: msg.data.created_at,
          detections: [],
          verdict: null,
        },
        ...prev,
      ].slice(0, 200));
    } else if (msg.kind === "verdict") {
      setEvents((prev) =>
        prev.map((e) =>
          e.id === msg.data.event_id
            ? {
                ...e,
                verdict: {
                  id: msg.data.id,
                  decision: msg.data.decision,
                  risk_score: msg.data.risk_score,
                  likelihood: msg.data.likelihood,
                  impact: msg.data.impact,
                  dominant_factor: msg.data.dominant_factor,
                  narrative: msg.data.narrative,
                },
              }
            : e
        )
      );
    }
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="display text-2xl font-bold tracking-wide">Monitor</h1>
        <div className="flex gap-2">
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="rounded-sm border border-border bg-background px-2 py-1.5 text-sm"
          >
            <option value="">All event types</option>
            <option value="prompt">Prompt</option>
            <option value="tool_call">Tool call</option>
            <option value="api_request">API request</option>
            <option value="output">Output</option>
          </select>
          <select
            value={decisionFilter}
            onChange={(e) => setDecisionFilter(e.target.value)}
            className="rounded-sm border border-border bg-background px-2 py-1.5 text-sm"
          >
            <option value="">All verdicts</option>
            <option value="allow">Allow</option>
            <option value="wait">Wait</option>
            <option value="block">Block</option>
          </select>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-muted-foreground border-b border-border">
                <tr>
                  <th className="text-left px-3 py-2">Time</th>
                  <th className="text-left px-3 py-2">Session</th>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-left px-3 py-2">Source</th>
                  <th className="text-left px-3 py-2">Payload</th>
                  <th className="text-left px-3 py-2">Risk</th>
                  <th className="text-left px-3 py-2">Verdict</th>
                  <th className="text-left px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id} className="border-b border-border/50 hover:bg-surface-hover">
                    <td className="px-3 py-2 mono text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(e.created_at).toLocaleTimeString()}
                    </td>
                    <td className="px-3 py-2 mono text-xs text-muted-foreground">
                      {e.session_id ? (
                        <Link href={`/graph/${e.session_id}`} className="hover:underline text-primary">
                          {e.session_id.slice(0, 8)}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-2"><Badge>{e.event_type}</Badge></td>
                    <td className="px-3 py-2 text-xs">{e.source}</td>
                    <td className="px-3 py-2 mono text-xs text-muted-foreground max-w-[240px] truncate">
                      {JSON.stringify(e.payload)}
                    </td>
                    <td className="px-3 py-2 mono text-xs">{e.verdict ? e.verdict.risk_score.toFixed(2) : "—"}</td>
                    <td className="px-3 py-2"><VerdictBadge decision={e.verdict?.decision} pending={!e.verdict} /></td>
                    <td className="px-3 py-2">
                      {e.verdict?.id && (
                        <Link href={`/reports/${e.verdict.id}`} className="text-xs text-primary hover:underline">
                          Report
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
                {events.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-3 py-8 text-center text-sm text-muted-foreground">
                      No events match this filter yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
