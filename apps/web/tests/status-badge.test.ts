import { describe, expect, it } from "vitest";
import { statusLabel, statusTone } from "../components/StatusBadge";

describe("status helpers", () => {
  it("formats status labels for readable badges", () => {
    expect(statusLabel("completed_with_warnings")).toBe("Completed With Warnings");
  });

  it("maps operational failure states to the bad tone", () => {
    expect(statusTone("failed")).toBe("bad");
    expect(statusTone("unavailable")).toBe("bad");
  });

  it("maps queued and running states to a visible notice tone", () => {
    expect(statusTone("queued")).toBe("notice");
    expect(statusTone("running")).toBe("notice");
  });
});
