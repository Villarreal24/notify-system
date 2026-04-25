"use client";

import { useActionState } from "react";

import { submitNotification } from "@/app/actions";
import type { OptimisticLogAction } from "@/components/notification-dashboard";
import {
  initialNotificationSubmitState,
  type NotificationSubmitState,
} from "@/lib/notification-submit-state";
import type { Category } from "@/lib/api";

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
    const category = categories.find((item) => item.id === categoryId);

    if (Number.isInteger(categoryId) && categoryId > 0 && message) {
      const temporaryId = `optimistic-${crypto.randomUUID()}`;
      onOptimisticLogAction({
        type: "add",
        log: {
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
          created_at: new Date().toISOString(),
        },
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
