import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createOperationalTestRun, listRuns } from "../lib/api/client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("API client", () => {
  it("uses NEXT_PUBLIC_API_BASE_URL and parses run lists", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ run_id: "RUN-1" }],
    });
    vi.stubGlobal("fetch", fetchMock);

    const runs = await listRuns({ limit: 5, agentId: "AGT-1" });

    expect(runs).toEqual([{ run_id: "RUN-1" }]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/v1/runs?limit=5&offset=0&agent_id=AGT-1",
      expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) }),
    );
  });

  it("posts the safe operational test run request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: "RUN-2", status: "queued", task_id: "TASK-1" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await createOperationalTestRun();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/runs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ trigger_type: "manual" }),
      }),
    );
  });

  it("raises API errors with server details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        json: async () => ({ detail: "Operational database unavailable" }),
      }),
    );

    await expect(listRuns()).rejects.toEqual(
      new ApiError("Operational database unavailable", 503),
    );
  });
});
