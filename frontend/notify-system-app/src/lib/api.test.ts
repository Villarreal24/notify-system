import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";

import { ApiError, createNotification } from "./api";

describe("ApiError", () => {
  it("preserves status and code", () => {
    const err = new ApiError("not found", 404, "CATEGORY_NOT_FOUND", "Category 9");
    expect(err.status).toBe(404);
    expect(err.code).toBe("CATEGORY_NOT_FOUND");
    expect(err.message).toBe("not found");
  });
});

describe("createNotification on failed fetch", () => {
  const original = globalThis.fetch;

  beforeEach(() => {
    process.env.API_BASE_URL = "http://localhost:8000";
  });

  afterEach(() => {
    globalThis.fetch = original;
    vi.restoreAllMocks();
  });

  it("throws ApiError with code from JSON body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: async () =>
        JSON.stringify({
          code: "CATEGORY_NOT_FOUND",
          detail: "Category 999 does not exist",
        }),
    });

    await expect(
      createNotification({ category_id: 1, message: "Hi" }),
    ).rejects.toMatchObject({ status: 404, code: "CATEGORY_NOT_FOUND" });
  });
});
