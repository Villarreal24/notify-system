import type { NotificationLog } from "@/lib/api";

export type OptimisticLogAction =
  | { type: "add"; log: NotificationLog }
  | { type: "confirmMany"; temporaryId: string; logs: NotificationLog[] }
  | { type: "rollback"; temporaryId: string };

export function isOptimisticLogId(id: string): boolean {
  return id.startsWith("optimistic-");
}
