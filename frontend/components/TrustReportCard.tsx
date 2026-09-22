import { Card, CardContent, CardHeader, CardTitle } from "./Card";
import { Badge, VerdictBadge } from "./Badge";
import { RiskGauge } from "./RiskGauge";
import type { DetectionResult, Decision } from "@/lib/types";

interface Props {
  decision: Decision;
  riskScore: number;
  likelihood: number;
  impact: number;
  alpha: number;
  dominantFactor: string;
  detectorBreakdown: DetectionResult[];
  narrative?: string | null;
  compact?: boolean;
}

export function TrustReportCard({
  decision,
  riskScore,
  likelihood,
  impact,
  alpha,
  dominantFactor,
  detectorBreakdown,
  narrative,
  compact,
}: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Trust report</CardTitle>
        <VerdictBadge decision={decision} />
      </CardHeader>
      <CardContent className="space-y-4">
        <RiskGauge score={riskScore} />

        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-sm border border-border p-2">
            <div className="text-[11px] text-muted-foreground">Likelihood (L)</div>
            <div className="mono text-lg">{likelihood.toFixed(2)}</div>
          </div>
          <div className="rounded-sm border border-border p-2">
            <div className="text-[11px] text-muted-foreground">Impact (I)</div>
            <div className="mono text-lg">{impact.toFixed(2)}</div>
          </div>
          <div className="rounded-sm border border-border p-2">
            <div className="text-[11px] text-muted-foreground">α</div>
            <div className="mono text-lg">{alpha.toFixed(2)}</div>
          </div>
        </div>

        <div className="text-xs mono text-muted-foreground border border-border rounded-sm p-2">
          R = α·L + (1-α)·I = {alpha.toFixed(2)}×{likelihood.toFixed(2)} + {(1 - alpha).toFixed(2)}×{impact.toFixed(2)} ={" "}
          <span className="text-foreground font-semibold">{riskScore.toFixed(3)}</span>
        </div>

        <div className="text-xs">
          Dominant factor: <Badge tone="primary">{dominantFactor}</Badge>
        </div>

        {narrative && (
          <div className="text-sm border-l-2 border-primary/40 pl-3 text-muted-foreground italic">
            {narrative}
          </div>
        )}

        {!compact && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-foreground">Detector breakdown</div>
            {detectorBreakdown.map((d) => (
              <div key={d.detector_name} className="rounded-sm border border-border p-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{d.detector_name}</span>
                  <Badge tone={d.triggered ? "danger" : "default"}>score {d.score.toFixed(2)}</Badge>
                </div>
                {d.evidence.length > 0 ? (
                  <ul className="mt-1 space-y-1">
                    {d.evidence.map((e, i) => (
                      <li key={i} className="text-xs text-muted-foreground mono">
                        [{e.label}] {e.detail}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-xs text-muted-foreground mt-1">no evidence</div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
