import { NotificationDashboard } from "@/components/notification-dashboard";
import { getCategories, getNotificationLogs } from "@/lib/api";

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
      ? "Could not load categories. Check that the API is running and the database is migrated and seeded."
      : null;
  const logsError =
    logsResult.status === "rejected"
      ? "Could not load delivery history. Check that the API is running and the database is ready."
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
