export type Category = {
  id: number;
  name: string;
};

export type NotificationLog = {
  id: string;
  message: string;
  /** null: legacy or incomplete row; optimistic placeholders may set nulls too */
  category_id: number | null;
  category_name: string | null;
  /** null only for optimistic UI placeholders in some cases */
  channel_id: number | null;
  channel_name: string | null;
  user_id: string | null;
  user_name: string | null;
  status: "PENDING" | "SUCCESS" | "FAILED";
  error_message: string | null;
  created_at: string;
};

export type NotificationPayload = {
  category_id: number;
  message: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly body?: unknown;

  constructor(message: string, status: number, code?: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

// Server-only: base URL of the FastAPI app (RSC and Server Actions).
const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const raw = await response.text();
    let code: string | undefined;
    let detail: unknown = raw;
    try {
      const data = JSON.parse(raw) as { code?: string; detail?: unknown };
      code = data.code;
      detail = data.detail ?? data;
    } catch {
      // non-JSON error body; keep text
    }
    const messageFromBody =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail) && response.status === 422
          ? "Validation error"
          : "Request failed";
    throw new ApiError(
      messageFromBody || `Request failed with ${response.status}`,
      response.status,
      code,
      detail,
    );
  }

  return response.json() as Promise<T>;
}

export async function getCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export async function getNotificationLogs(
  limit?: number,
): Promise<NotificationLog[]> {
  const q = limit != null ? `?limit=${encodeURIComponent(String(limit))}` : "";
  return request<NotificationLog[]>(`/notification-logs${q}`);
}

export async function createNotification(
  payload: NotificationPayload,
): Promise<NotificationLog[]> {
  return request<NotificationLog[]>("/notifications", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
