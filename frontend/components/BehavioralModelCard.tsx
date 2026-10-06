"use client";

/** Policy page card: status of the trained behavioral model (item 2). */
import { useEffect, useState } from "react";
import { api, type BehavioralModelStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";
import { Badge } from "@/components/Badge";

const TOP_EDGES = 8;

export function BehavioralModelCard() {
  const [status, setStatus] = useState<BehavioralModelStatus | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.getBehavioralModel().then(setStatus).catch(() => setFailed(true));
  }, []);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Behavioral model</CardTitle>
        {status && (status.trained ? <Badge tone="success">Trained</Badge> : <Badge tone="warning">Not trained</Badge>)}
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {failed && <p className="text-muted-foreground">Couldn&apos;t load the model status.</p>}
        {!status && !failed && <p className="text-muted-foreground">Loading…</p>}

        {status && !status.trained && (
          <p className="text-muted-foreground" data-testid="behavioral-untrained">
            Model not trained yet — use the Sandbox with a Groq key to build history. It has{" "}
            <span className="mono text-foreground">{status.tool_calls}</span> of the{" "}
            <span className="mono text-foreground">{status.min_tool_calls_required}</span> allowed tool calls it
            needs, and retrains each time the backend restarts. Until then only the exfiltration-chain rule runs.
          </p>
        )}

        {status && status.trained && (
          <>
            <p className="text-muted-foreground">
              Learned from <span className="mono text-foreground">{status.sessions}</span> sessions and{" "}
              <span className="mono text-foreground">{status.tool_calls}</span> allowed tool calls (Laplace k ={" "}
              {status.smoothing_k}). Retrains each time the backend restarts.
            </p>
            <div className="space-y-1">
              <div className="text-xs font-semibold">Most likely transitions</div>
              {[...status.edges]
                .sort((a, b) => b.observed_count - a.observed_count)
                .slice(0, TOP_EDGES)
                .map((e) => (
                  <div
                    key={`${e.source}->${e.target}`}
                    className="flex items-center justify-between text-xs mono rounded-sm border border-border px-2 py-1"
                  >
                    <span>
                      {e.source} → {e.target}
                    </span>
                    <span className="text-muted-foreground">
                      p={e.probability.toFixed(2)} · seen {e.observed_count}×
                    </span>
                  </div>
                ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}