import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BehavioralModelCard } from "@/components/BehavioralModelCard";
import { api, type BehavioralModelStatus } from "@/lib/api";

const base: BehavioralModelStatus = {
  trained: false,
  min_tool_calls_required: 20,
  sessions: 1,
  tool_calls: 3,
  transitions: 3,
  tools: ["file_read"],
  smoothing_k: 0.5,
  edges: [],
};

afterEach(() => vi.restoreAllMocks());

describe("BehavioralModelCard", () => {
  it("says the model is not trained yet, with progress", async () => {
    vi.spyOn(api, "getBehavioralModel").mockResolvedValue(base);
    render(<BehavioralModelCard />);
    expect(await screen.findByText("Not trained")).toBeInTheDocument();
    expect(screen.getByTestId("behavioral-untrained")).toHaveTextContent("Model not trained yet");
    expect(screen.getByTestId("behavioral-untrained")).toHaveTextContent("3 of the 20");
  });

  it("shows training stats and learned transitions once trained", async () => {
    vi.spyOn(api, "getBehavioralModel").mockResolvedValue({
      ...base,
      trained: true,
      sessions: 8,
      tool_calls: 24,
      edges: [
        { source: "file_read", target: "file_write", probability: 0.85, observed_count: 8 },
        { source: "session_start", target: "file_read", probability: 0.8, observed_count: 8 },
      ],
    });
    render(<BehavioralModelCard />);
    expect(await screen.findByText("Trained")).toBeInTheDocument();
    expect(screen.getByText("file_read → file_write")).toBeInTheDocument();
    expect(screen.getByText(/p=0.85 · seen 8×/)).toBeInTheDocument();
  });
});