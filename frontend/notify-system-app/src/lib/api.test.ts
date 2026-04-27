import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";

import {
  ApiError,
  createNotification,
  getCategories,
  getNotificationLogs,
} from "./api";

describe("ApiError", () => {
  it("preserves status and code", () => {
    const err = new ApiError("not found", 404, "CATEGORY_NOT_FOUND", "Category 9");
    expect(err.status).toBe(404);
    expect(err.code).toBe("CATEGORY_NOT_FOUND");
    expect(err.message).toBe("not found");
  });
});

describe("api requests", () => {
  const original = globalThis.fetch;

  beforeEach(() => {
    process.env.API_BASE_URL = "http://localhost:8000";
  });

  afterEach(() => {
    globalThis.fetch = original;
    vi.restoreAllMocks();
  });

  it("fetches categories from the backend", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        { id: 1, name: "Sports" },
        { id: 2, name: "Finance" },
      ],
    });

    await expect(getCategories()).resolves.toEqual([
      { id: 1, name: "Sports" },
      { id: 2, name: "Finance" },
    ]);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/categories",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("fetches log history with a limit query", async () => {
    const logs = [
      {
        id: "log-1",
        message: "Sports update",
        category_id: 1,
        category_name: "Sports",
        channel_id: 2,
        channel_name: "E-Mail",
        user_id: "user-1",
        user_name: "Alice",
        status: "SUCCESS",
        error_message: null,
        created_at: "2026-04-26T00:00:00Z",
      },
    ];
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => logs,
    });

    await expect(getNotificationLogs(25)).resolves.toEqual(logs);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/notification-logs?limit=25",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("fetches log history without a limit query", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    await expect(getNotificationLogs()).resolves.toEqual([]);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/notification-logs",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("posts notification payloads to the backend", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    await createNotification({ category_id: 1, message: "Hi" });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/notifications",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ category_id: 1, message: "Hi" }),
      }),
    );
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

  it("throws ApiError with raw text for non-JSON failures", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      text: async () => "Service unavailable",
    });

    await expect(getCategories()).rejects.toMatchObject({
      status: 503,
      message: "Service unavailable",
      body: "Service unavailable",
    });
  });

  it("throws ApiError with validation detail for 422 responses", async () => {
    const detail = [
      {
        type: "string_too_long",
        loc: ["body", "message"],
        msg: "String should have at most 1000 characters",
      },
    ];
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: async () =>
        JSON.stringify({
          code: "VALIDATION_ERROR",
          detail,
        }),
    });

    await expect(
      createNotification({ category_id: 1, message: "Hi" }),
    ).rejects.toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Validation error",
      body: detail,
    });
  });
});
