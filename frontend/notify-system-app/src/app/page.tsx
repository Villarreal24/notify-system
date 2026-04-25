import { NotificationDashboard } from "@/components/notification-dashboard";
import { getCategories, getNotificationLogs } from "@/lib/api";

export default async function Home() {
  const [categoriesResult, logsResult] = await Promise.allSettled([
    getCategories(),
    getNotificationLogs(),
  ]);

  const categories =
    categoriesResult.status === "fulfilled" ? categoriesResult.value : [];
  const logs = logsResult.status === "fulfilled" ? logsResult.value : [];
  const logsError =
    logsResult.status === "rejected"
      ? "No se pudo cargar el historial de logs. Revisa la API o la migracion de la base de datos."
      : null;

  return (
    <NotificationDashboard
      categories={categories}
      logs={logs}
      logsError={logsError}
    />
  );
}
