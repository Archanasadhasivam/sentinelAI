"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { TrustReport } from "@/lib/types";
import { TrustReportCard } from "@/components/TrustReportCard";
import { Card, CardContent } from "@/components/Card";

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<TrustReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getReport(params.id)
      .then(setReport)
      .catch((err) => setError(err.message));
  }, [params.id]);

  if (error) {
    return (
      <Card>
        <CardContent className="text-sm text-danger">Couldn&apos;t load report: {error}</CardContent>
      </Card>
    );
  }

  if (!report) {
    return (
      <Card>
        <CardContent className="text-sm text-muted-foreground">Loading report…</CardContent>
      </Card>
    );
  }

  const breakdown = (report.structured_report?.detector_breakdown ?? []).map((d: any) => ({
    detector_name: d.detector_name ?? d.detector,
    score: d.score,
    triggered: d.triggered,
    evidence: d.evidence ?? [],
    metadata: d.metadata ?? {},
  }));

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Trust Report</h1>
        <p className="text-xs text-muted-foreground mono">
          verdict {report.verdict_id.slice(0, 8)} · event {report.event_id.slice(0, 8)} ·{" "}
          {new Date(report.created_at).toLocaleString()}
        </p>
      </div>
      <TrustReportCard
        decision={report.decision}
        riskScore={report.risk_score}
        likelihood={report.likelihood}
        impact={report.impact}
        alpha={report.alpha}
        dominantFactor={report.dominant_factor}
        detectorBreakdown={breakdown}
        narrative={report.narrative}
      />
    </div>
  );
}
