import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TrustReportCard } from "@/components/TrustReportCard";
import type { DetectionResult } from "@/lib/types";

const detections: DetectionResult[] = [
  {
    detector_name: "prompt_injection",
    score: 0.9,
    triggered: true,
    evidence: [{ detector: "prompt_injection", label: "regex:role_override", detail: "matched 'ignore all previous'", weight: 0.6 } as any],
    metadata: {},
  },
  { detector_name: "sensitive_data_leakage", score: 0, triggered: false, evidence: [], metadata: {} },
];

const base = {
  decision: "block" as const,
  riskScore: 0.84,
  likelihood: 0.9,
  impact: 0.6,
  alpha: 0.8,
  dominantFactor: "prompt_injection",
  detectorBreakdown: detections,
};

describe("TrustReportCard", () => {
  it("shows the verdict, risk formula and dominant factor", () => {
    render(<TrustReportCard {...base} />);
    expect(screen.getByText("Block")).toBeInTheDocument();
    expect(screen.getByText("0.840")).toBeInTheDocument(); // R in the formula line
    expect(screen.getAllByText("prompt_injection").length).toBeGreaterThan(0);
  });

  it("lists every detector with its evidence", () => {
    render(<TrustReportCard {...base} />);
    expect(screen.getByText("score 0.90")).toBeInTheDocument();
    expect(screen.getByText(/regex:role_override/)).toBeInTheDocument();
    expect(screen.getByText("no evidence")).toBeInTheDocument();
  });

  it("shows the narrative when there is one", () => {
    render(<TrustReportCard {...base} narrative="Classic role-override attack." />);
    expect(screen.getByText("Classic role-override attack.")).toBeInTheDocument();
  });

  it("hides the detector breakdown in compact mode", () => {
    render(<TrustReportCard {...base} compact />);
    expect(screen.queryByText("Detector breakdown")).not.toBeInTheDocument();
  });
});