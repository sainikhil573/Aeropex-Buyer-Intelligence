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

  it("uses review language without presenting accepted as verified", () => {
    expect(statusLabel("needs_review")).toBe("Needs Review");
    expect(statusTone("accepted")).toBe("notice");
    expect(statusTone("rejected")).toBe("bad");
  });

  it("maps extraction states for observation review", () => {
    expect(statusTone("success")).toBe("good");
    expect(statusTone("partial")).toBe("warn");
    expect(statusTone("unstructured")).toBe("warn");
  });
});
