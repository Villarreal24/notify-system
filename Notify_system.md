# Notification system — system context & project requirements

> **Agent role:** Act as a senior full-stack engineer. Build a *Notification System* (engineering challenge) that ingests messages by category and delivers them to subscribed users through their preferred channels (SMS, E-mail, Push).

**Engineering focus:** clean architecture, SOLID, design patterns, fault tolerance, and solid performance.

---

## 1. Project overview

| Aspect | Description |
|--------|-------------|
| **Goal** | Route notifications by category; deliver via user-subscribed channels. |
| **Quality bar** | Maintainable layers, background processing (do not block the HTTP request path for delivery). |

---

## 2. Tech stack (strict constraints)

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.10+, FastAPI |
| **Database** | PostgreSQL (local via Docker Compose) |
| **ORM** | SQLAlchemy 2.0 (async preferred) + Alembic for migrations |
| **Frontend** | Next.js (App Router), React 19, TypeScript |
| **Styling** | Tailwind CSS (Server Components) + Chakra UI (Client Components) |

---

## 3. Backend architecture

### 3.1 Clean architecture / DDD-style layout

```
api/           — controllers / routes
services/      — business logic
repositories/  — data access abstraction
models/        — SQLAlchemy entities
schemas/       — Pydantic DTOs
strategies/    — notification channel implementations
```

### 3.2 Required design patterns

- **Strategy:** `INotificationChannel` (or equivalent); concrete `SmsStrategy`, `EmailStrategy`, `PushStrategy` to isolate send logic.
- **Factory:** `ChannelFactory` to construct the right strategy from user preferences.
- **Repository:** e.g. `UserRepository`, `LogRepository` — **services must not** talk to the ORM directly.
- **Dependency injection:** FastAPI `Depends()` wiring repositories → services → routes.

### 3.3 Performance & fault tolerance

> **Required:** do **not** process notification delivery **synchronously** inside the HTTP handler.

- Use FastAPI **BackgroundTasks** (or an agreed equivalent) for the notification work queue.
- After payload validation, respond with **`202 Accepted`** immediately.

---

## 4. Frontend architecture

### 4.1 Patterns to follow

- **Container / presentational:** Server Components as containers (data, log history); Client Components for interactivity and UI (e.g. Chakra form).
- **Custom hooks:** encapsulate non-trivial state and Server Action wiring (e.g. `useNotificationSubmit`).
- **Composition:** avoid prop drilling; use `children` where it helps the server/client boundary.

### 4.2 State management (strict rule)

> **Do not** use global state managers (Zustand, Redux, Context API) for **business** logic.

- Rely on React 19 native hooks (`useActionState`, `useFormStatus`, `useOptimistic`), Server Actions, and props. Use `useState` only for small local UI toggles if needed.

---

## 5. Database schema

Implement SQLAlchemy models and initial seed data for:

| Table | Fields / notes |
|-------|----------------|
| `users` | `id`, `name`, `email`, `phone_number` |
| `categories` | `id`, `name` — seed: Sports, Finance, Movies |
| `channels` | `id`, `name` — seed: SMS, E-Mail, Push |
| `user_subscriptions` | `user_id`, `category_id` — many-to-many |
| `user_channels` | `user_id`, `channel_id` — many-to-many |
| `notification_logs` | `id`, `message`, `category_id`, `channel_id`, `user_id`, `created_at` |

---

## 6. Testing (Pytest)

- **Unit** tests for services and strategies.
- **Mock** database access in unit tests.
- **API** tests using FastAPI `TestClient`.

---

## 7. Implementation order (for the agent)

Follow **this order** unless explicitly told otherwise:

1. SQLAlchemy models and database schema / migrations.
2. Pydantic schemas (DTOs).
3. Strategy + factory for notification channels.
4. Repositories and services (business logic + background tasks).
5. FastAPI API routers.
6. Next.js frontend.

---

## Notes for LLM / agent consumption

- Sections marked **strict**, **required**, or **do not** are **normative**, not optional suggestions.
- If unspecified, prefer the simplest design that still matches the stack and patterns above.
