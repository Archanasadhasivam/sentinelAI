"use client";

import { useEffect, useState } from "react";
import { api, API_BASE } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";
import { Badge } from "@/components/Badge";

export default function SettingsPage() {
  const [status, setStatus] = useState<{ configured: boolean; degraded: boolean; models: Record<string, string> } | null>(null);
  const [health, setHealth] = useState<{ status: string } | null>(null);

  useEffect(() => {
    api.getGroqStatus().then(setStatus).catch(() => setStatus(null));
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-lg font-semibold">Settings</h1>

      <Card>
        <CardHeader><CardTitle>Backend connection</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">API base URL</span>
            <span className="mono">{API_BASE}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            {health ? <Badge tone="success">Connected</Badge> : <Badge tone="danger">Unreachable</Badge>}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Groq semantic layer</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">API key configured</span>
            {status?.configured ? <Badge tone="success">Yes</Badge> : <Badge tone="warning">No — degraded mode</Badge>}
          </div>
          {status && (
            <>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Reasoning model</span>
                <span className="mono text-xs">{status.models.reasoning}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Fast model</span>
                <span className="mono text-xs">{status.models.fast}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Safety model</span>
                <span className="mono text-xs">{status.models.safety}</span>
              </div>
            </>
          )}
          {!status?.configured && (
            <p className="text-xs text-muted-foreground pt-2 border-t border-border">
              Add <code className="mono">GROQ_API_KEY</code> to <code className="mono">backend/.env</code> and
              restart the backend to enable the semantic prompt-injection layer, TrustReport narratives, and the
              Agent Sandbox&apos;s live reasoning/tool use. Deterministic detectors run at full strength either way.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
