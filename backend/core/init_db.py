"""Database initialization, schema creation, and PL/pgSQL triggers."""

import asyncio
from sqlalchemy import text
from backend.core.database import Base, engine
import backend.models  # Ensure all models are registered

TRIGGER_DDL = """
-- 1. Trigger to make audit_logs strictly append-only (blocks UPDATE and DELETE)
CREATE OR REPLACE FUNCTION trg_audit_logs_no_update_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only and cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;
CREATE TRIGGER trg_audit_logs_immutable
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION trg_audit_logs_no_update_delete();


-- 2. Trigger enforcing four-eyes principle on approvals (requester != approver)
CREATE OR REPLACE FUNCTION trg_approvals_four_eyes_check()
RETURNS TRIGGER AS $$
DECLARE
    v_requester_id UUID;
BEGIN
    SELECT requested_by INTO v_requester_id FROM wipe_requests WHERE id = NEW.request_id;
    IF v_requester_id IS NOT NULL AND v_requester_id = NEW.approver_id THEN
        RAISE EXCEPTION 'Four-eyes rule violation: Requester cannot approve their own wipe request';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_approvals_four_eyes ON approvals;
CREATE TRIGGER trg_approvals_four_eyes
BEFORE INSERT OR UPDATE ON approvals
FOR EACH ROW
EXECUTE FUNCTION trg_approvals_four_eyes_check();


-- 3. Trigger enforcing approval validation on wipe_jobs insertion
CREATE OR REPLACE FUNCTION trg_wipe_jobs_require_valid_approval()
RETURNS TRIGGER AS $$
DECLARE
    v_approval RECORD;
BEGIN
    SELECT * INTO v_approval FROM approvals WHERE id = NEW.approval_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Job validation error: approval_id does not exist';
    END IF;
    IF v_approval.request_id <> NEW.request_id THEN
        RAISE EXCEPTION 'Job validation error: approval request_id mismatch';
    END IF;
    IF v_approval.decision <> 'APPROVED' THEN
        RAISE EXCEPTION 'Job validation error: approval must be APPROVED';
    END IF;
    IF v_approval.expires_at < NOW() THEN
        RAISE EXCEPTION 'Job validation error: approval has expired';
    END IF;
    IF v_approval.used_at IS NOT NULL AND v_approval.used_at < (NOW() - INTERVAL '1 minute') THEN
        RAISE EXCEPTION 'Job validation error: approval token already used';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_wipe_jobs_valid_approval ON wipe_jobs;
CREATE TRIGGER trg_wipe_jobs_valid_approval
BEFORE INSERT ON wipe_jobs
FOR EACH ROW
EXECUTE FUNCTION trg_wipe_jobs_require_valid_approval();


-- 4. Trigger enforcing legal state machine transitions on wipe_requests
CREATE OR REPLACE FUNCTION trg_wipe_requests_state_transition()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = NEW.status THEN
        RETURN NEW;
    END IF;

    IF OLD.status = 'DRAFT' AND NEW.status IN ('PENDING_APPROVAL', 'CANCELLED') THEN
        RETURN NEW;
    ELSIF OLD.status = 'PENDING_APPROVAL' AND NEW.status IN ('APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED') THEN
        RETURN NEW;
    ELSIF OLD.status = 'APPROVED' AND NEW.status IN ('QUEUED', 'EXPIRED', 'CANCELLED') THEN
        RETURN NEW;
    ELSIF OLD.status = 'QUEUED' AND NEW.status IN ('RUNNING', 'CANCELLED', 'FAILED') THEN
        RETURN NEW;
    ELSIF OLD.status = 'RUNNING' AND NEW.status IN ('VERIFYING', 'FAILED') THEN
        RETURN NEW;
    ELSIF OLD.status = 'VERIFYING' AND NEW.status IN ('COMPLETED', 'FAILED') THEN
        RETURN NEW;
    ELSE
        RAISE EXCEPTION 'Illegal wipe request transition from % to %', OLD.status, NEW.status;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_wipe_requests_transition ON wipe_requests;
CREATE TRIGGER trg_wipe_requests_transition
BEFORE UPDATE OF status ON wipe_requests
FOR EACH ROW
EXECUTE FUNCTION trg_wipe_requests_state_transition();
"""


async def init_database() -> None:
    """Initializes tables and creates PL/pgSQL triggers in PostgreSQL."""
    async with engine.begin() as conn:
        # Create all declared tables
        await conn.run_sync(Base.metadata.create_all)

        # Split trigger blocks by semicolon/double newline and execute individually
        statements = [
            """
            CREATE OR REPLACE FUNCTION trg_audit_logs_no_update_delete()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'audit_logs is append-only and cannot be modified or deleted';
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;",
            """
            CREATE TRIGGER trg_audit_logs_immutable
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION trg_audit_logs_no_update_delete();
            """,
            """
            CREATE OR REPLACE FUNCTION trg_approvals_four_eyes_check()
            RETURNS TRIGGER AS $$
            DECLARE
                v_requester_id UUID;
            BEGIN
                SELECT requested_by INTO v_requester_id FROM wipe_requests WHERE id = NEW.request_id;
                IF v_requester_id IS NOT NULL AND v_requester_id = NEW.approver_id THEN
                    RAISE EXCEPTION 'Four-eyes rule violation: Requester cannot approve their own wipe request';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP TRIGGER IF EXISTS trg_approvals_four_eyes ON approvals;",
            """
            CREATE TRIGGER trg_approvals_four_eyes
            BEFORE INSERT OR UPDATE ON approvals
            FOR EACH ROW
            EXECUTE FUNCTION trg_approvals_four_eyes_check();
            """,
            """
            CREATE OR REPLACE FUNCTION trg_wipe_jobs_require_valid_approval()
            RETURNS TRIGGER AS $$
            DECLARE
                v_approval RECORD;
            BEGIN
                SELECT * INTO v_approval FROM approvals WHERE id = NEW.approval_id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'Job validation error: approval_id does not exist';
                END IF;
                IF v_approval.request_id <> NEW.request_id THEN
                    RAISE EXCEPTION 'Job validation error: approval request_id mismatch';
                END IF;
                IF v_approval.decision <> 'APPROVED' THEN
                    RAISE EXCEPTION 'Job validation error: approval must be APPROVED';
                END IF;
                IF v_approval.expires_at < NOW() THEN
                    RAISE EXCEPTION 'Job validation error: approval has expired';
                END IF;
                IF v_approval.used_at IS NOT NULL AND v_approval.used_at < (NOW() - INTERVAL '1 minute') THEN
                    RAISE EXCEPTION 'Job validation error: approval token already used';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP TRIGGER IF EXISTS trg_wipe_jobs_valid_approval ON wipe_jobs;",
            """
            CREATE TRIGGER trg_wipe_jobs_valid_approval
            BEFORE INSERT ON wipe_jobs
            FOR EACH ROW
            EXECUTE FUNCTION trg_wipe_jobs_require_valid_approval();
            """,
            """
            CREATE OR REPLACE FUNCTION trg_wipe_requests_state_transition()
            RETURNS TRIGGER AS $$
            BEGIN
                IF OLD.status = NEW.status THEN
                    RETURN NEW;
                END IF;

                IF OLD.status = 'DRAFT' AND NEW.status IN ('PENDING_APPROVAL', 'CANCELLED') THEN
                    RETURN NEW;
                ELSIF OLD.status = 'PENDING_APPROVAL' AND NEW.status IN ('APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED') THEN
                    RETURN NEW;
                ELSIF OLD.status = 'APPROVED' AND NEW.status IN ('QUEUED', 'EXPIRED', 'CANCELLED') THEN
                    RETURN NEW;
                ELSIF OLD.status = 'QUEUED' AND NEW.status IN ('RUNNING', 'CANCELLED', 'FAILED') THEN
                    RETURN NEW;
                ELSIF OLD.status = 'RUNNING' AND NEW.status IN ('VERIFYING', 'FAILED') THEN
                    RETURN NEW;
                ELSIF OLD.status = 'VERIFYING' AND NEW.status IN ('COMPLETED', 'FAILED') THEN
                    RETURN NEW;
                ELSE
                    RAISE EXCEPTION 'Illegal wipe request transition from % to %', OLD.status, NEW.status;
                END IF;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP TRIGGER IF EXISTS trg_wipe_requests_transition ON wipe_requests;",
            """
            CREATE TRIGGER trg_wipe_requests_transition
            BEFORE UPDATE OF status ON wipe_requests
            FOR EACH ROW
            EXECUTE FUNCTION trg_wipe_requests_state_transition();
            """,
        ]

        for stmt in statements:
            await conn.execute(text(stmt.strip()))


if __name__ == "__main__":
    asyncio.run(init_database())
    print("Database tables, triggers, and functions successfully initialized.")
