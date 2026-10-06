import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RiskGauge } from "@/components/RiskGauge";

function scoreColour(score: number) {
  render(<RiskGauge score={score} />);
  return screen.getByText(Math.min(Math.max(score, 0), 1).toFixed(2)).style.color;
}

describe("RiskGauge", () => {
  it("shows the score with two decimals", () => {
    render(<RiskGauge score={0.456} />);
    expect(screen.getByText("0.46")).toBeInTheDocument();
    expect(screen.getByText("risk score R")).toBeInTheDocument();
  });

  it("colours the score by band: allow, wait, block", () => {
    expect(scoreColour(0.2)).toContain("--success");
  });
  it("is in the wait band at the wait threshold", () => {
    expect(scoreColour(0.45)).toContain("--warning");
  });
  it("is in the block band at the block threshold", () => {
    expect(scoreColour(0.75)).toContain("--danger");
  });

  it("clamps scores outside 0..1", () => {
    render(<RiskGauge score={1.7} />);
    expect(screen.getByText("1.00")).toBeInTheDocument();
  });

  it("respects custom thresholds", () => {
    render(<RiskGauge score={0.3} waitThreshold={0.1} blockThreshold={0.25} />);
    expect(screen.getByText("0.30").style.color).toContain("--danger");
  });
});