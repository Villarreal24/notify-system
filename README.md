# Notification System

Sistema full-stack para enviar notificaciones por categoria a usuarios suscritos y registrar cada entrega por canal.

## Stack

- Backend: FastAPI, SQLAlchemy async, PostgreSQL.
- Frontend: Next.js App Router, React 19, TypeScript, Tailwind CSS y Chakra UI.
- Base de datos local: Docker Compose con `postgres_schema.sql` como inicializador.

## Ejecutar Localmente

1. Levantar PostgreSQL:

```bash
docker compose up -d db
```

2. Instalar y ejecutar backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

La API queda disponible en `http://localhost:8000`.

3. Instalar y ejecutar frontend:

```bash
cd frontend/notify-system-app
bun install
bun run dev
```

La app queda disponible en `http://localhost:3000`.

## Contratos Principales

- `GET /health`
- `GET /categories`
- `GET /channels`
- `GET /notification-logs`
- `POST /notifications`

`POST /notifications` responde `202 Accepted` despues de validar el payload y procesa el envio simulado con `BackgroundTasks`.

## Decisiones

- Los canales `SMS`, `E-Mail` y `Push Notification` estan implementados como estrategias simuladas.
- `postgres_schema.sql` se mantiene como fuente de inicializacion local para Docker.
- Las rutas delegan en servicios y repositorios; la ORM queda encapsulada en la capa `repositories`.
