"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useEventStream } from "@/lib/ws";
import type { Alert, WSMessage } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";
import { Badge } from "@/components/Badge";
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from "recharts";
import { ShieldAlert, ShieldCheck, ShieldX, Activity } from "lucide-react";

export default function OverviewPage() {
  const [counters, setCounters] = useState({ total: 0, blocked: 0, waiting: 0, allowed: 0 });
  const [riskHistory, setRiskHistory] = useState<{ t: number; r: number }[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    api.listEvents({ limit: 100 }).then((res) => {
      const c = { total: res.total, blocked: 0, waiting: 0, allowed: 0 };
      const hist: { t: number; r: number }[] = [];
      res.events
        .slice()
        .reverse()
        .forEach((e: any, i: number) => {
          if (e.verdict) {
            if (e.verdict.decision === "block") c.blocked++;
            else if (e.verdict.decision === "wait") c.waiting++;
            else c.allowed++;
            hist.push({ t: i, r: e.verdict.risk_score });
          }
        });
      setCounters(c);
      setRiskHistory(hist);
    });
    api.listAlerts().then((res) => setAlerts(res.alerts.slice(0, 8)));
  }, []);

  useEventStream((msg: WSMessage) => {
    if (msg.kind === "verdict") {
      setCounters((c) => ({
        total: c.total + 1,
        blocked: c.blocked + (msg.data.decision === "block" ? 1 : 0),
        waiting: c.waiting + (msg.data.decision === "wait" ? 1 : 0),
        allowed: c.allowed + (msg.data.decision === "allow" ? 1 : 0),
      }));
      setRiskHistory((h) => [...h, { t: h.length, r: msg.data.risk_score }].slice(-50));
    } else if (msg.kind === "alert") {
      setAlerts((a) => [
        { id: msg.data.id, event_id: msg.data.event_id, tier: msg.data.tier, message: msg.data.message, acknowledged: false, created_at: msg.data.created_at },
        ...a,
      ].slice(0, 8));
    }
  });

  const avgRisk = riskHistory.length
    ? riskHistory.reduce((s, x) => s + x.r, 0) / riskHistory.length
    : 0;

  const statCards = [
    { label: "Events today", value: counters.total, icon: Activity, dot: "bg-primary" },
    { label: "Blocked", value: counters.blocked, icon: ShieldX, dot: "bg-danger" },
    { label: "Held for review", value: counters.waiting, icon: ShieldAlert, dot: "bg-warning" },
    { label: "Allowed", value: counters.allowed, icon: ShieldCheck, dot: "bg-success" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="display text-2xl font-bold tracking-wide">Overview</h1>
        <p className="text-sm text-muted-foreground">
          Live posture of the SentinelAI middleware gateway.{" "}
          <Link href="/playground" className="text-primary hover:underline">
            Open the Agent Sandbox
          </Link>
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {statCards.map(({ label, value, icon: Icon, dot }) => (
          <div key={label} className="rounded-md border border-border bg-surface p-3.5">
            <div className="flex items-center justify-between mb-2">
              <span className={`inline-block w-1.5 h-1.5 rounded-full ${dot}`} aria-hidden />
              <Icon size={15} className="text-muted-foreground" />
            </div>
            <div className="display text-3xl font-bold leading-none">{value}</div>
            <div className="text-xs text-muted-foreground mt-1.5">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Risk score over time (avg {avgRisk.toFixed(2)})</CardTitle>
          </CardHeader>
          <CardContent className="h-56">
            {riskHistory.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No verdicts yet — try the Playground.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={riskHistory}>
                  <YAxis domain={[0, 1]} hide />
                  <Tooltip
                    contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))" }}
                    formatter={(v: number) => v.toFixed(2)}
                  />
                  <Line type="monotone" dataKey="r" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent alerts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 max-h-56 overflow-y-auto">
            {alerts.length === 0 && <div className="text-sm text-muted-foreground">No alerts yet.</div>}
            {alerts.map((a) => (
              <div key={a.id} className="flex items-start gap-2 text-sm">
                <Badge tone={a.tier === "critical" ? "danger" : a.tier === "warning" ? "warning" : "default"}>
                  {a.tier}
                </Badge>
                <span className="text-muted-foreground">{a.message}</span>
              </div>
            ))}
            <Link href="/alerts" className="block text-xs text-primary hover:underline pt-1">
              View all alerts
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
