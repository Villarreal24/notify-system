# Notification System

Full-stack system for sending category-based notifications to subscribed users and recording each delivery by user and channel. The project focuses on clean architecture, background processing, fault tolerance, optimistic UI, and SSR-driven updates from Next.js.

## Stack

- Backend: FastAPI, async SQLAlchemy, PostgreSQL, Pydantic, and Tenacity.
- Frontend: Next.js App Router, React 19, TypeScript, Tailwind CSS, and Chakra UI.
- Local database: PostgreSQL with `postgres_schema.sql` for fresh initialization and `postgres_migration_fault_tolerance.sql` for existing databases.

## Architecture

```text
backend/
  api/           FastAPI routes and BackgroundTasks
  services/      business rules and delivery orchestration
  repositories/  SQLAlchemy data access
  models/        ORM entities
  schemas/       DTOs Pydantic
  strategies/    SMS, E-Mail, and Push channels

frontend/notify-system-app/
  src/app/        Server Components and Server Actions
  src/components/ Chakra UI Client Components
  src/hooks/      useActionState and useOptimistic wiring
  src/lib/        API client and shared types
```

## Notification Flow

`POST /notifications` does not send notifications in the request path. The endpoint validates the payload, finds users subscribed to the selected category, and creates `PENDING` logs for each concrete delivery:

```text
notification + category
  -> subscribed users
  -> preferred channels per user
  -> notification_logs per user/channel
  -> BackgroundTasks receives the log_ids list
```

The endpoint responds with `202 Accepted` and the list of created logs. Each log includes `category_id`, `channel_id`, `user_id`, `status`, and `error_message`, so the history displays real deliveries such as “To Alice Johnson / E-Mail” instead of an aggregate send order.

## Background, Concurrency, And Performance

The actual delivery happens in FastAPI `BackgroundTasks`. `NotificationService.deliver_pending_logs()` loads pending logs and processes the batch with controlled concurrency:

- Uses `asyncio.Semaphore(50)` to limit simultaneous deliveries.
- Builds one async task per log.
- Runs the batch with `asyncio.gather(..., return_exceptions=True)`.
- A single delivery failure does not cancel the rest of the batch.
- Once the batch finishes, each log is updated to `SUCCESS` or `FAILED`.
- Status commits/rollbacks are performed in an ordered way after gathering results.

This model simulates a basic pool/rate limit: it avoids a blocking sequential loop while also preventing unlimited send fan-out.

## Simulated Latency, Retries, And Failures

Channels implement the Strategy pattern and simulate external providers:

- `SMS`: `1.0s` to `3.0s` latency.
- `E-Mail`: `0.5s` to `2.0s` latency.
- `Push Notification`: `1.0s` to `4.0s` latency.
- Each provider has a `15%` random failure rate to simulate timeouts/errors.
- Tenacity retries delivery up to `3` times with a fixed `2s` wait.

If retries are exhausted, only that log is marked as `FAILED` and stores `error_message`. If delivery succeeds, the log is marked as `SUCCESS`.

## Frontend, SSR, And Optimistic UI

The main page is a Server Component in `src/app/page.tsx`. It loads categories and logs from the server with `getCategories()` and `getNotificationLogs()`. If the history request fails, the UI displays an error instead of hiding it as an empty list.

The form uses:

- `useActionState` to execute the `submitNotification` Server Action.
- `useOptimistic` to show immediate feedback.
- `confirmMany` to replace the temporary placeholder with all real logs returned by the backend.
- `rollback` if the backend could not register the logs.

The Server Action calls `revalidatePath("/")` after creating logs. The dashboard also runs `router.refresh()` when the browser tab regains focus or becomes visible again, with a `1s` guard to avoid duplicate requests. Because API fetches use `cache: "no-store"`, refresh requests fresh backend data and lets the UI reconcile `PENDING -> SUCCESS/FAILED` changes without a manual reload.

## Database

`notification_logs` records deliveries by user/channel and includes:

- `status`: `PENDING`, `SUCCESS`, or `FAILED`.
- `error_message`: nullable details when a delivery fails.
- relationships with `categories`, `channels`, and `users`.

For a fresh database, use `postgres_schema.sql`. For an existing database created before status tracking, apply:

```bash
PGPASSWORD=adminpassword psql -h localhost -U admin -d notification_system \
  -f postgres_migration_fault_tolerance.sql
```

## Main Contracts

- `GET /health`
- `GET /categories`
- `GET /channels`
- `GET /notification-logs`
- `POST /notifications`

`POST /notifications` returns a list of `PENDING` logs:

```json
[
  {
    "id": "uuid",
    "message": "Game starts",
    "category_id": 1,
    "category_name": "Sports",
    "channel_id": 2,
    "channel_name": "E-Mail",
    "user_id": "uuid",
    "user_name": "Alice Johnson",
    "status": "PENDING",
    "error_message": null,
    "created_at": "2026-04-25T18:40:23.907705Z"
  }
]
```

## Running Locally

1. Start the local PostgreSQL database with Docker Compose:

The root `docker-compose.yaml` file creates a local PostgreSQL container named `notification_db`, exposes it on `localhost:5432`, and initializes the `notification_system` database with `postgres_schema.sql` the first time the volume is created.

```bash
docker compose up -d
```

2. Install and run the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API is available at `http://localhost:8000`.

3. Install and run the frontend:

```bash
cd frontend/notify-system-app
npm install
npm run dev
```

The app is available at `http://localhost:3000`.

## Validation

Backend:

```bash
cd backend
.venv/bin/python -m pytest
```

Frontend:

```bash
cd frontend/notify-system-app
npm run lint
```

## Technical Decisions

- FastAPI routes delegate to services and repositories; ORM access is encapsulated in `repositories`.
- Channels are resolved with Strategy + Factory.
- The HTTP response is fast (`202 Accepted`); the heavy work happens in background.
- Logs represent real deliveries, not aggregate orders.
- The UI combines SSR for the initial history, Server Actions for mutations, `useOptimistic` for immediate feedback, and focus-based refresh to reconcile asynchronous status changes.
