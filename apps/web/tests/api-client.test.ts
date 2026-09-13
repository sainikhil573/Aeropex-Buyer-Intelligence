import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  canonicalizeObservation,
  createOperationalTestRun,
  getObservation,
  getObservationReview,
  listObservations,
  listRuns,
  updateObservationReview,
} from "../lib/api/client";

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

  it("lists observations with review and source filters", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ observation_id: "OBS-1", review_status: "accepted" }],
    });
    vi.stubGlobal("fetch", fetchMock);

    const observations = await listObservations({
      reviewStatus: "accepted",
      productId: "PRD-RED-CHILLI",
      sourceId: "SRC-1",
      extractionStatus: "success",
    });

    expect(observations[0].review_status).toBe("accepted");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/v1/observations?limit=50&offset=0&review_status=accepted&source_id=SRC-1&product_id=PRD-RED-CHILLI&extraction_status=success",
      expect.any(Object),
    );
  });

  it("gets observation detail and review state", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ observation_id: "OBS-1", raw_text: "<b>raw</b>" }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ observation_id: "OBS-1", status: "unreviewed" }) });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getObservation("OBS-1")).resolves.toEqual({ observation_id: "OBS-1", raw_text: "<b>raw</b>" });
    await expect(getObservationReview("OBS-1")).resolves.toEqual({ observation_id: "OBS-1", status: "unreviewed" });
  });

  it("patches review status and notes", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ observation_id: "OBS-1", status: "needs_review", review_notes: "Check source" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await updateObservationReview("OBS-1", { status: "needs_review", review_notes: "Check source" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/observations/OBS-1/review",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ status: "needs_review", review_notes: "Check source" }),
      }),
    );
  });

  it("posts observation canonicalization requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ observation_id: "OBS-1", status: "created", buyer_id: "BUY-1" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await canonicalizeObservation("OBS-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/observations/OBS-1/canonicalize",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
