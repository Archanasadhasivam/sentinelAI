import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge, VerdictBadge } from "@/components/Badge";

describe("Badge", () => {
  it("renders its text with the tone's colour", () => {
    render(<Badge tone="danger">Blocked</Badge>);
    const text = screen.getByText("Blocked");
    expect(text).toBeInTheDocument();
    expect(text.parentElement).toHaveClass("text-danger");
  });

  it("uses the default tone when none is given", () => {
    render(<Badge>Plain</Badge>);
    expect(screen.getByText("Plain").parentElement).toHaveClass("text-muted-foreground");
  });
});

describe("VerdictBadge", () => {
  it.each([
    ["allow", "Allow", "text-success"],
    ["wait", "Wait", "text-warning"],
    ["block", "Block", "text-danger"],
  ] as const)("shows %s as '%s'", (decision, label, cls) => {
    render(<VerdictBadge decision={decision} />);
    expect(screen.getByText(label).parentElement).toHaveClass(cls);
  });

  it("shows Pending while there is no decision yet", () => {
    render(<VerdictBadge pending />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});