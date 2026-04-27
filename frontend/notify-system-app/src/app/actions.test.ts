import { revalidatePath } from "next/cache";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { initialNotificationSubmitState } from "@/lib/notification-submit-state";

import { submitNotification } from "./actions";

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

const originalFetch = globalThis.fetch;

function formData(values: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) {
    data.set(key, value);
  }
  return data;
}

describe("submitNotification", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.API_BASE_URL = "http://localhost:8000";
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("rejects an invalid category before calling the API", async () => {
    globalThis.fetch = vi.fn();

    const result = await submitNotification(
      initialNotificationSubmitState,
      formData({ category_id: "0", message: "Hello" }),
    );

    expect(result).toEqual({
      status: "error",
      message: "Select a valid category.",
      logs: [],
    });
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("rejects an empty message before calling the API", async () => {
    globalThis.fetch = vi.fn();

    const result = await submitNotification(
      initialNotificationSubmitState,
      formData({ category_id: "1", message: "   " }),
    );

    expect(result).toEqual({
      status: "error",
      message: "Enter a message to send.",
      logs: [],
    });
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("rejects messages longer than the backend max length", async () => {
    globalThis.fetch = vi.fn();

    const result = await submitNotification(
      initialNotificationSubmitState,
      formData({ category_id: "1", message: "x".repeat(1001) }),
    );

    expect(result).toEqual({
      status: "error",
      message: "Message is too long (max 1000 characters).",
      logs: [],
    });
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("maps 404 category errors to a specific user message", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: async () =>
        JSON.stringify({
          code: "CATEGORY_NOT_FOUND",
          detail: "Category 999 does not exist",
        }),
    });

    const result = await submitNotification(
      initialNotificationSubmitState,
      formData({ category_id: "999", message: "Hello" }),
    );

    expect(result).toMatchObject({
      status: "error",
      message: "The selected category was not found.",
      logs: [],
    });
  });

  it("maps 422 validation errors to a specific user message", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: async () =>
        JSON.stringify({
          code: "VALIDATION_ERROR",
          detail: [],
        }),
    });

    const result = await submitNotification(
      initialNotificationSubmitState,
      formData({ category_id: "1", message: "Hello" }),
    );

    expect(result).toMatchObject({
      status: "error",
      message:
        "The request was rejected due to invalid input. Check the message length (max 1,000 characters) and selected category.",
      logs: [],
    });
  });

  it("returns success and revalidates the dashboard after API acceptance", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: "log-1",
          message: "Hello",
          category_id: 1,
          category_name: "Sports",
          channel_id: 2,
          channel_name: "E-Mail",
          user_id: "user-1",
          user_name: "Alice",
          status: "PENDING",
          error_message: null,
          created_at: "2026-04-26T00:00:00Z",
        },
      ],
    });

    const result = await submitNotification(
      initialNotificationSubmitState,
      formData({ category_id: "1", message: " Hello " }),
    );

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/notifications",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ category_id: 1, message: "Hello" }),
      }),
    );
    expect(revalidatePath).toHaveBeenCalledWith("/");
    expect(result.status).toBe("success");
    expect(result.logs).toHaveLength(1);
  });
});
