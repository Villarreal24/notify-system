"use client";

import { useActionState } from "react";

import { submitNotification } from "@/app/actions";
import type { OptimisticLogAction } from "@/lib/notification-types";
import {
  initialNotificationSubmitState,
  type NotificationSubmitState,
} from "@/lib/notification-submit-state";
import type { Category } from "@/lib/api";
import { buildOptimisticLog } from "@/lib/optimistic-notifications";

type UseNotificationSubmitOptions = {
  categories: Category[];
  onOptimisticLogAction: (action: OptimisticLogAction) => void;
};

export function useNotificationSubmit({
  categories,
  onOptimisticLogAction,
}: UseNotificationSubmitOptions) {
  return useActionState(async (
    previousState: NotificationSubmitState,
    formData: FormData,
  ) => {
    const categoryId = Number(formData.get("category_id"));
    const message = String(formData.get("message") ?? "").trim();

    if (Number.isInteger(categoryId) && categoryId > 0 && message) {
      const temporaryId = `optimistic-${crypto.randomUUID()}`;
      onOptimisticLogAction({
        type: "add",
        log: buildOptimisticLog({
          categories,
          categoryId,
          message,
          temporaryId,
          createdAt: new Date().toISOString(),
        }),
      });

      const result = await submitNotification(previousState, formData);
      if (result.status === "success") {
        onOptimisticLogAction({
          type: "confirmMany",
          temporaryId,
          logs: result.logs,
        });
      } else {
        onOptimisticLogAction({ type: "rollback", temporaryId });
      }

      return result;
    }

    return submitNotification(previousState, formData);
  }, initialNotificationSubmitState);
}
