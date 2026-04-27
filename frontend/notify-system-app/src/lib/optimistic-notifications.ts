import type { Category, NotificationLog } from "@/lib/api";
import type { OptimisticLogAction } from "@/lib/notification-types";

export function buildOptimisticLog({
  categories,
  categoryId,
  message,
  temporaryId,
  createdAt,
}: {
  categories: Category[];
  categoryId: number;
  message: string;
  temporaryId: string;
  createdAt: string;
}): NotificationLog {
  const category = categories.find((item) => item.id === categoryId);

  return {
    id: temporaryId,
    message,
    category_id: categoryId,
    category_name: category?.name ?? null,
    channel_id: null,
    channel_name: null,
    user_id: null,
    user_name: null,
    status: "PENDING",
    error_message: null,
    created_at: createdAt,
  };
}

export function applyOptimisticLogAction(
  currentLogs: NotificationLog[],
  action: OptimisticLogAction,
): NotificationLog[] {
  if (action.type === "rollback") {
    return currentLogs.filter((log) => log.id !== action.temporaryId);
  }

  if (action.type === "confirmMany") {
    const confirmedIds = new Set(action.logs.map((log) => log.id));
    return [
      ...action.logs,
      ...currentLogs.filter(
        (log) => log.id !== action.temporaryId && !confirmedIds.has(log.id),
      ),
    ];
  }

  return [
    action.log,
    ...currentLogs.filter((log) => log.id !== action.log.id),
  ];
}
