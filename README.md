# Notification System

Full-stack system for sending category-based notifications to subscribed users and recording each delivery by user and channel. The project focuses on clean architecture, background processing, failure handling, optimistic UI, and server-driven updates in Next.js.

## Stack

- **Backend:** FastAPI, async SQLAlchemy, PostgreSQL, Pydantic, Alembic, Tenacity.
- **Frontend:** Next.js App Router, React 19, TypeScript, Tailwind CSS, and Chakra UI.
- **Database:** PostgreSQL. **SQLAlchemy models + Alembic** are the source of truth. `postgres_schema.sql` is only for Docker’s first-time init to match the current revision.

## Architecture

```text
backend/
  api/            FastAPI routes, BackgroundTasks, exception handlers
  services/       Business rules and delivery orchestration
  repositories/   SQLAlchemy data access
  models/         ORM entities
  schemas/        Pydantic DTOs
  strategies/     SMS, E-mail, and Push channels
  alembic/        Migrations
  core/           Settings and database engine

frontend/notify-system-app/
  src/app/         Server Components and Server Actions
  src/components/ Chakra client components
  src/hooks/      useActionState and optimistic delivery wiring
  src/lib/        API client, shared types, error types
```

## Notification flow

`POST /notifications` does not deliver on the request thread. The handler validates the payload, loads subscribers in the **active** (non–soft-deleted) user set, and creates one `PENDING` `notification_log` per user and preferred channel. The API responds with **202 Accepted** and the list of created logs. FastAPI `BackgroundTasks` then runs the delivery job with controlled concurrency and bounded retries (see `NotificationService`).

## Background delivery, concurrency, and fault tolerance

Delivery runs in a background task. Batched sends use a semaphore sized from settings (`NOTIFICATION_DELIVERY_CONCURRENCY`, capped by the DB connection pool) so application concurrency does not outpace SQLAlchemy’s pool. Retries are implemented with Tenacity. Transient and simulated provider failures are recorded with **sanitized** `error_message` values, not raw stack traces.

> **Note:** `BackgroundTasks` is in-process only. A hard process crash after the HTTP response can leave rows in `PENDING` until a follow-up or worker exists; see `Notify_system.md` and treat this as a demo-appropriate choice unless you add a durable queue (Redis, SQS, etc.).

## Database, migrations, and seeds

1. **Preferred:** `docker compose up -d` (optional first-time `postgres_schema.sql` load), then from `backend/` run:

   ```bash
   .venv/bin/alembic upgrade head
   .venv/bin/python -m seed_data
   ```

2. If the database was created from an older one-off script, or you need a clean state, **drop the volume** or `alembic stamp head` / `alembic upgrade` as appropriate.

- **Soft deletes:** `users.deleted_at` marks logical deletion; subscribers with a timestamp are excluded from new sends; historical `notification_logs` still reference the user id.
- **Seeding:** `seed_data` is idempotent and mirrors the sample data in `postgres_schema.sql`.

## Environment

- **Backend** — copy [backend/.env.example](backend/.env.example) to `backend/.env` and adjust. Never commit real secrets. `.env` is gitignored.
- **Frontend (server only)** — copy [frontend/notify-system-app/.env.example](frontend/notify-system-app/.env.example) to `frontend/notify-system-app/.env` if the API is not on `http://localhost:8000`. Use `API_BASE_URL` (not `NEXT_PUBLIC_*`) unless the browser must call the API directly.

## API contracts (high level)

- `GET /health` — liveness: no database call; use for Kubernetes liveness so brief DB outages do not restart the pod.
- `GET /health/ready` — readiness: `SELECT 1`; returns 503 if the database is unavailable; use for readiness and dependency checks.
- `GET /categories`, `GET /channels`
- `GET /notification-logs?limit=` (1–100)
- `POST /notifications` — 202, returns created log rows in `PENDING` state

Errors from the app use a consistent shape where applicable:

```json
{ "code": "CATEGORY_NOT_FOUND", "detail": "…" }
```

## Running locally

1. **PostgreSQL**

   ```bash
   docker compose up -d
   ```

2. **Backend**

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   alembic upgrade head
   python -m seed_data
   fastapi dev --reload
   ```

   API: `http://localhost:8000`

3. **Frontend**

   ```bash
   cd frontend/notify-system-app
   bun install
   bun dev
   ```

   App: `http://localhost:3000`

## Validation

**Backend**

```bash
cd backend
.venv/bin/python -m pytest
```

**Frontend**

```bash
cd frontend/notify-system-app
npm run lint
npm test
npm run build
```

## Technical decisions (evaluation summary)

- **Layering:** routes delegate to services; services use repositories; no raw SQL in routes.
- **Patterns:** strategy + factory for channels, repository abstraction, DTOs with Pydantic, dependency injection via `Depends()`.
- **DB:** foreign keys, indexes on `notification_logs (user_id)`, `(status, created_at)`, and `created_at DESC` for history; `message` length aligned to API validation; Alembic for evolution.
- **Security posture:** the challenge does not require authentication; the API should still not leak internal errors to clients, and `error_message` in the DB is sanitized.
- **Frontend:** `useActionState` / `useOptimistic` without global state for business data; `ApiError` maps HTTP + JSON codes to user messages; all UI copy is English.
