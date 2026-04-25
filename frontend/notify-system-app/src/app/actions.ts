"use server";

import { revalidatePath } from "next/cache";

import { createNotification } from "@/lib/api";
import type { NotificationSubmitState } from "@/lib/notification-submit-state";

export async function submitNotification(
  _previousState: NotificationSubmitState,
  formData: FormData,
): Promise<NotificationSubmitState> {
  const categoryId = Number(formData.get("category_id"));
  const message = String(formData.get("message") ?? "").trim();

  if (!Number.isInteger(categoryId) || categoryId <= 0) {
    return {
      status: "error",
      message: "Selecciona una categoria valida.",
      logs: [],
    };
  }

  if (!message) {
    return {
      status: "error",
      message: "Escribe un mensaje para enviar.",
      logs: [],
    };
  }

  try {
    const logs = await createNotification({ category_id: categoryId, message });
    revalidatePath("/");
    return {
      status: "success",
      message: `Notificacion aceptada. ${logs.length} entregas se procesaran en background.`,
      logs,
    };
  } catch {
    return {
      status: "error",
      message:
        "No se pudo registrar el log. Revisa tu conexion a internet o que la API este activa.",
      logs: [],
    };
  }
}
