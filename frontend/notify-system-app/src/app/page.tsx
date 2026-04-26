import { NotificationDashboard } from "@/components/notification-dashboard";
import {
  ApiError,
  getCategories,
  getNotificationLogs,
} from "@/lib/api";

export const dynamic = "force-dynamic";

function describeRejection(
  reason: unknown,
  fallback: string,
): string {
  if (reason instanceof ApiError) {
    return `${reason.message} (HTTP ${reason.status}${
      reason.code ? `, ${reason.code}` : ""
    })`;
  }
  if (reason instanceof Error) {
    return reason.message
      ? `${reason.message} (${fallback})`
      : fallback;
  }
  return fallback;
}

export default async function Home() {
  const [categoriesResult, logsResult] = await Promise.allSettled([
    getCategories(),
    getNotificationLogs(100),
  ]);

  const categories =
    categoriesResult.status === "fulfilled" ? categoriesResult.value : [];
  const logs = logsResult.status === "fulfilled" ? logsResult.value : [];
  const categoriesError =
    categoriesResult.status === "rejected"
      ? describeRejection(
          categoriesResult.reason,
          "Check that the API is running and the database is migrated and seeded.",
        )
      : null;
  const logsError =
    logsResult.status === "rejected"
      ? describeRejection(
          logsResult.reason,
          "Check that the API is running, API_BASE_URL is correct for the server, and the database is ready.",
        )
      : null;

  return (
    <NotificationDashboard
      categories={categories}
      categoriesError={categoriesError}
      logs={logs}
      logsError={logsError}
    />
  );
}
