"use server";

import { revalidatePath } from "next/cache";

import { ApiError, createNotification } from "@/lib/api";
import type { NotificationSubmitState } from "@/lib/notification-submit-state";

const MESSAGE_MAX = 1_000;

function describeApiError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404 && err.code === "CATEGORY_NOT_FOUND") {
      return "The selected category was not found.";
    }
    if (err.status === 422) {
      return "The request was rejected due to invalid input. Check the message length (max 1,000 characters) and selected category.";
    }
    if (err.status === 500) {
      return "The server failed to process the request. Please try again in a few moments.";
    }
    if (err.status === 0 || err.message === "Failed to fetch") {
      return "Network error. Check that the API is running and your connection is stable.";
    }
    return err.message || "The API returned an error.";
  }
  return "Could not create notification logs. Check your connection and that the API is running.";
}

export async function submitNotification(
  _previousState: NotificationSubmitState,
  formData: FormData,
): Promise<NotificationSubmitState> {
  const categoryId = Number(formData.get("category_id"));
  const message = String(formData.get("message") ?? "").trim();

  if (!Number.isInteger(categoryId) || categoryId <= 0) {
    return {
      status: "error",
      message: "Select a valid category.",
      logs: [],
    };
  }

  if (!message) {
    return {
      status: "error",
      message: "Enter a message to send.",
      logs: [],
    };
  }

  if (message.length > MESSAGE_MAX) {
    return {
      status: "error",
      message: `Message is too long (max ${MESSAGE_MAX} characters).`,
      logs: [],
    };
  }

  try {
    const logs = await createNotification({ category_id: categoryId, message });
    revalidatePath("/");
    return {
      status: "success",
      message: `Notification accepted. ${logs.length} delivery job(s) will be processed in the background.`,
      logs,
    };
  } catch (err) {
    return {
      status: "error",
      message: describeApiError(err),
      logs: [],
    };
  }
}
