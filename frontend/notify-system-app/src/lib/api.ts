export type Category = {
  id: number;
  name: string;
};

export type NotificationLog = {
  id: string;
  message: string;
  category_id: number | null;
  category_name: string | null;
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

const API_BASE_URL =
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: init?.method === "POST" ? "no-store" : "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export async function getNotificationLogs(): Promise<NotificationLog[]> {
  return request<NotificationLog[]>("/notification-logs");
}

export async function createNotification(
  payload: NotificationPayload,
): Promise<NotificationLog[]> {
  return request<NotificationLog[]>("/notifications", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
