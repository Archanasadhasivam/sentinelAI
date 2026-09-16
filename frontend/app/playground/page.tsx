"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useEventStream } from "@/lib/ws";
import type { SentinelEvent, WSMessage } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";
import { AttackPresetMenu } from "@/components/AttackPresetMenu";
import { EventStreamPanel } from "@/components/EventStreamPanel";
import { Badge } from "@/components/Badge";
import { RotateCcw, Send } from "lucide-react";

interface ChatTurn {
  role: "user" | "agent" | "system";
  text: string;
}

export default function PlaygroundPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [events, setEvents] = useState<SentinelEvent[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.createSession("Playground session").then((s) => setSessionId(s.id));
    api.getGroqStatus().then((s) => setDegraded(!s.configured));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  useEventStream((msg: WSMessage) => {
    if (!sessionId) return;
    if (msg.kind === "event_created") {
      if (msg.data.session_id !== sessionId) return;
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
    } else if (msg.kind === "detection_result") {
      setEvents((prev) =>
        prev.map((e) =>
          e.id === msg.data.event_id
            ? {
                ...e,
                detections: [
                  ...e.detections.filter((d) => d.detector_name !== msg.data.detector_name),
                  {
                    detector_name: msg.data.detector_name,
                    score: msg.data.score,
                    triggered: msg.data.triggered,
                    evidence: msg.data.evidence,
                    metadata: msg.data.metadata,
                  },
                ],
              }
            : e
        )
      );
    } else if (msg.kind === "verdict") {
      setEvents((prev) =>
        prev.map((e) =>
          e.id === msg.data.event_id
            ? {
                ...e,
                status: msg.data.decision,
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

  async function send(text: string) {
    if (!sessionId || !text.trim() || sending) return;
    setSending(true);
    setTurns((t) => [...t, { role: "user", text }]);
    setInput("");
    try {
      const result = await api.sendMessage(sessionId, text);
      setTurns((t) => [...t, { role: "agent", text: result.reply }]);
    } catch (err: any) {
      setTurns((t) => [...t, { role: "system", text: `Error: ${err.message}` }]);
    } finally {
      setSending(false);
    }
  }

  async function resetSession() {
    if (!sessionId) return;
    await api.resetSession(sessionId);
    setTurns([]);
    setEvents([]);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-4">
      <div className="flex flex-col h-[calc(100vh-6.5rem)]">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-semibold">Agent Sandbox</h1>
          <div className="flex items-center gap-2">
            {degraded && <Badge tone="warning">No Groq key — degraded mode</Badge>}
            <AttackPresetMenu onSelect={(text) => send(text)} />
            <button
              onClick={resetSession}
              className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-surface-hover"
            >
              <RotateCcw size={14} />
              Reset
            </button>
          </div>
        </div>

        <Card className="flex-1 flex flex-col overflow-hidden">
          <CardContent className="flex-1 overflow-y-auto space-y-3">
            {turns.length === 0 && (
              <div className="text-sm text-muted-foreground">
                Chat with the sandboxed agent, or pick an attack preset above to see SentinelAI intercept it live.
              </div>
            )}
            {turns.map((t, i) => (
              <div key={i} className={`flex ${t.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    t.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : t.role === "system"
                      ? "bg-danger/10 text-danger border border-danger/30"
                      : "bg-surface-hover"
                  }`}
                >
                  {t.text}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </CardContent>
          <div className="border-t border-border p-3 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              placeholder="Ask the sandbox agent to do something..."
              className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              disabled={!sessionId || sending}
            />
            <button
              onClick={() => send(input)}
              disabled={!sessionId || sending}
              className="rounded-md bg-primary text-primary-foreground px-3 py-2 disabled:opacity-50"
            >
              <Send size={16} />
            </button>
          </div>
        </Card>
      </div>

      <div className="h-[calc(100vh-6.5rem)]">
        <EventStreamPanel events={events} title="Interception → Detection → Verdict" />
      </div>
    </div>
  );
}
