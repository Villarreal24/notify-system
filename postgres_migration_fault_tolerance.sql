-- Apply fault-tolerant notification log fields to an existing database.
-- postgres_schema.sql is used for fresh databases; this file is safe to rerun.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'log_status') THEN
        CREATE TYPE log_status AS ENUM ('PENDING', 'SUCCESS', 'FAILED');
    END IF;
END
$$;

ALTER TABLE notification_logs
    ADD COLUMN IF NOT EXISTS status log_status,
    ADD COLUMN IF NOT EXISTS error_message TEXT;

UPDATE notification_logs
SET status = 'PENDING'
WHERE status IS NULL;

ALTER TABLE notification_logs
    ALTER COLUMN status SET DEFAULT 'PENDING',
    ALTER COLUMN status SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_notification_logs_status ON notification_logs(status);
