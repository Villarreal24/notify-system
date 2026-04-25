import type { NotificationLog } from "@/lib/api";

export type NotificationSubmitState = {
  status: "idle" | "success" | "error";
  message: string;
  logs: NotificationLog[];
};

export const initialNotificationSubmitState: NotificationSubmitState = {
  status: "idle",
  message: "",
  logs: [],
};
