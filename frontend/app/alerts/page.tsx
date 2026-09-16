"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useEventStream } from "@/lib/ws";
import type { Alert, WSMessage } from "@/lib/types";
import { Card, CardContent } from "@/components/Card";
import { Badge } from "@/components/Badge";
import { Check } from "lucide-react";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [tier, setTier] = useState("");

  async function reload() {
    const res = await api.listAlerts(tier || undefined);
    setAlerts(res.alerts);
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tier]);

  useEventStream((msg: WSMessage) => {
    if (msg.kind === "alert") {
      setAlerts((prev) => [
        {
          id: msg.data.id,
          event_id: msg.data.event_id,
          tier: msg.data.tier,
          message: msg.data.message,
          acknowledged: false,
          created_at: msg.data.created_at,
        },
        ...prev,
      ]);
    }
  });

  async function acknowledge(id: string) {
    await api.acknowledgeAlert(id);
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a)));
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Alerts</h1>
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="rounded-md border border-border bg-background px-2 py-1.5 text-sm"
        >
          <option value="">All tiers</option>
          <option value="critical">Critical (Tier 3 / Block)</option>
          <option value="warning">Warning (Tier 2 / Wait)</option>
          <option value="info">Info (Tier 1)</option>
        </select>
      </div>

      <div className="space-y-2">
        {alerts.length === 0 && (
          <Card>
            <CardContent className="text-sm text-muted-foreground">No alerts yet.</CardContent>
          </Card>
        )}
        {alerts.map((a) => (
          <Card key={a.id} className={a.acknowledged ? "opacity-60" : ""}>
            <CardContent className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Badge tone={a.tier === "critical" ? "danger" : a.tier === "warning" ? "warning" : "default"}>
                  {a.tier}
                </Badge>
                <div>
                  <div className="text-sm">{a.message}</div>
                  <div className="text-xs text-muted-foreground">{new Date(a.created_at).toLocaleString()}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Link href={`/monitor`} className="text-xs text-primary hover:underline">
                  View event
                </Link>
                {!a.acknowledged && (
                  <button
                    onClick={() => acknowledge(a.id)}
                    className="flex items-center gap-1 text-xs rounded-md border border-border px-2 py-1 hover:bg-surface-hover"
                  >
                    <Check size={12} /> Acknowledge
                  </button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
