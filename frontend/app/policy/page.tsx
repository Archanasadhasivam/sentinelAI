"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PolicyConfig } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";
import { Badge } from "@/components/Badge";
import { PlayCircle, Save } from "lucide-react";

function NumberField({
  label, value, onChange, min = 0, max = 1, step = 0.01,
}: { label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number }) {
  return (
    <label className="flex items-center justify-between gap-3 text-sm py-1.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-2">
        <input
          type="range" min={min} max={max} step={step} value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="w-32 accent-[hsl(var(--primary))]"
        />
        <span className="mono w-12 text-right">{value.toFixed(2)}</span>
      </span>
    </label>
  );
}

export default function PolicyPage() {
  const [policy, setPolicy] = useState<PolicyConfig | null>(null);
  const [rocWeights, setRocWeights] = useState<number[]>([]);
  const [dryRun, setDryRun] = useState<{ results: any[]; changed_count: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getPolicy().then((res) => {
      setPolicy(res.policy);
      setRocWeights(res.roc_weights_preview);
    });
  }, []);

  if (!policy) {
    return <div className="text-sm text-muted-foreground">Loading policy…</div>;
  }

  function update<K extends keyof PolicyConfig>(key: K, value: PolicyConfig[K]) {
    setPolicy((p) => (p ? { ...p, [key]: value } : p));
    setSaved(false);
  }

  async function save() {
    if (!policy) return;
    setSaving(true);
    try {
      await api.putPolicy(policy);
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  async function runDryRun() {
    if (!policy) return;
    const res = await api.dryRunPolicy(policy, 25);
    setDryRun(res);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold">Policy</h1>
          <div className="flex gap-2">
            <button
              onClick={runDryRun}
              className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-surface-hover"
            >
              <PlayCircle size={14} /> Dry run (last 25 events)
            </button>
            <button
              onClick={save}
              disabled={saving}
              className="flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-sm disabled:opacity-50"
            >
              <Save size={14} /> {saving ? "Saving…" : saved ? "Saved" : "Save"}
            </button>
          </div>
        </div>

        <Card>
          <CardHeader><CardTitle>Decision thresholds</CardTitle></CardHeader>
          <CardContent>
            <NumberField
              label="Wait threshold"
              value={policy.thresholds.wait}
              onChange={(v) => update("thresholds", { ...policy.thresholds, wait: v })}
            />
            <NumberField
              label="Block threshold"
              value={policy.thresholds.block}
              onChange={(v) => update("thresholds", { ...policy.thresholds, block: v })}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Risk formula: R = α·L + (1-α)·I</CardTitle></CardHeader>
          <CardContent>
            <NumberField
              label="α (likelihood weight)"
              value={policy.risk.alpha}
              onChange={(v) => update("risk", { ...policy.risk, alpha: v })}
            />
            <NumberField
              label="Impact floor"
              value={policy.risk.impact_floor}
              onChange={(v) => update("risk", { ...policy.risk, impact_floor: v })}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Detector weights (ROC-derived, see below)</CardTitle></CardHeader>
          <CardContent>
            {Object.entries(policy.detector_weights).map(([name, weight]) => (
              <NumberField
                key={name}
                label={name}
                value={weight}
                onChange={(v) => update("detector_weights", { ...policy.detector_weights, [name]: v })}
              />
            ))}
            {rocWeights.length > 0 && (
              <div className="mt-2 text-xs text-muted-foreground mono">
                ROC preview for {rocWeights.length} ranked detectors: [{rocWeights.join(", ")}]
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Action impact</CardTitle></CardHeader>
          <CardContent>
            {Object.entries(policy.action_impact).map(([name, weight]) => (
              <NumberField
                key={name}
                label={name}
                value={weight}
                onChange={(v) => update("action_impact", { ...policy.action_impact, [name]: v })}
              />
            ))}
          </CardContent>
        </Card>
      </div>

      <div>
        <Card>
          <CardHeader><CardTitle>Dry-run results</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {!dryRun && <div className="text-sm text-muted-foreground">Run a dry-run to preview how these settings would re-score recent events, without saving anything.</div>}
            {dryRun && (
              <>
                <div className="text-sm">
                  <Badge tone={dryRun.changed_count > 0 ? "warning" : "default"}>
                    {dryRun.changed_count} of {dryRun.results.length} verdicts would change
                  </Badge>
                </div>
                <div className="space-y-1.5 max-h-[70vh] overflow-y-auto">
                  {dryRun.results.map((r) => (
                    <div key={r.event_id} className={`flex items-center justify-between text-xs rounded-md border p-2 ${r.changed ? "border-warning/40 bg-warning/5" : "border-border"}`}>
                      <span className="mono text-muted-foreground">{r.event_id.slice(0, 8)} · {r.event_type}</span>
                      <span className="flex items-center gap-2">
                        <Badge>{r.original_decision}</Badge>
                        {r.changed && <span>→</span>}
                        {r.changed && <Badge tone={r.new_decision === "block" ? "danger" : r.new_decision === "wait" ? "warning" : "success"}>{r.new_decision}</Badge>}
                        <span className="mono">{r.new_risk_score.toFixed(2)}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
