-- RoomieRoster Audit Logging System
-- This migration adds comprehensive audit logging for all data modifications
-- Tracks WHO changed WHAT, WHEN, and stores both old and new values

-- ============================================================================
-- Part 1: Create Audit Log Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,

    -- What was changed
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),

    -- When and by whom
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(255),  -- Email of user who made the change
    ip_address INET,  -- IP address of the request
    user_agent TEXT,  -- Browser/client information

    -- What changed (stored as JSON for flexibility)
    old_values JSONB,  -- Previous state (NULL for INSERT)
    new_values JSONB,  -- New state (NULL for DELETE)
    changed_fields TEXT[],  -- List of fields that changed (UPDATE only)

    -- Additional context
    request_id VARCHAR(100),  -- For correlating related changes
    notes TEXT  -- Optional description of why the change was made
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_record_id ON audit_log(record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit_log(changed_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_by ON audit_log(changed_by);
CREATE INDEX IF NOT EXISTS idx_audit_log_operation ON audit_log(operation);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON audit_log(table_name, record_id);

-- ============================================================================
-- Part 2: Audit Trigger Function (Generic)
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    old_data JSONB;
    new_data JSONB;
    changed_fields TEXT[] := ARRAY[]::TEXT[];
    field_name TEXT;
BEGIN
    -- Convert row data to JSON
    IF (TG_OP = 'DELETE') THEN
        old_data := row_to_json(OLD)::JSONB;
        new_data := NULL;
    ELSIF (TG_OP = 'INSERT') THEN
        old_data := NULL;
        new_data := row_to_json(NEW)::JSONB;
    ELSIF (TG_OP = 'UPDATE') THEN
        old_data := row_to_json(OLD)::JSONB;
        new_data := row_to_json(NEW)::JSONB;

        -- Identify changed fields
        FOR field_name IN SELECT jsonb_object_keys(new_data)
        LOOP
            IF old_data->field_name IS DISTINCT FROM new_data->field_name THEN
                changed_fields := array_append(changed_fields, field_name);
            END IF;
        END LOOP;
    END IF;

    -- Insert audit record
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_fields
    ) VALUES (
        TG_TABLE_NAME,
        CASE
            WHEN TG_OP = 'DELETE' THEN (OLD.id)::INTEGER
            ELSE (NEW.id)::INTEGER
        END,
        TG_OP,
        old_data,
        new_data,
        CASE WHEN TG_OP = 'UPDATE' THEN changed_fields ELSE NULL END
    );

    -- Return appropriate row
    IF (TG_OP = 'DELETE') THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- Part 3: Apply Audit Triggers to All Tables
-- ============================================================================

-- Roommates table
DROP TRIGGER IF EXISTS audit_roommates_trigger ON roommates;
CREATE TRIGGER audit_roommates_trigger
    AFTER INSERT OR UPDATE OR DELETE ON roommates
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Chores table
DROP TRIGGER IF EXISTS audit_chores_trigger ON chores;
CREATE TRIGGER audit_chores_trigger
    AFTER INSERT OR UPDATE OR DELETE ON chores
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Sub-chores table
DROP TRIGGER IF EXISTS audit_sub_chores_trigger ON sub_chores;
CREATE TRIGGER audit_sub_chores_trigger
    AFTER INSERT OR UPDATE OR DELETE ON sub_chores
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Assignments table
DROP TRIGGER IF EXISTS audit_assignments_trigger ON assignments;
CREATE TRIGGER audit_assignments_trigger
    AFTER INSERT OR UPDATE OR DELETE ON assignments
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Shopping items table
DROP TRIGGER IF EXISTS audit_shopping_items_trigger ON shopping_items;
CREATE TRIGGER audit_shopping_items_trigger
    AFTER INSERT OR UPDATE OR DELETE ON shopping_items
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Requests table
DROP TRIGGER IF EXISTS audit_requests_trigger ON requests;
CREATE TRIGGER audit_requests_trigger
    AFTER INSERT OR UPDATE OR DELETE ON requests
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Laundry slots table
DROP TRIGGER IF EXISTS audit_laundry_slots_trigger ON laundry_slots;
CREATE TRIGGER audit_laundry_slots_trigger
    AFTER INSERT OR UPDATE OR DELETE ON laundry_slots
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Blocked time slots table
DROP TRIGGER IF EXISTS audit_blocked_time_slots_trigger ON blocked_time_slots;
CREATE TRIGGER audit_blocked_time_slots_trigger
    AFTER INSERT OR UPDATE OR DELETE ON blocked_time_slots
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- ============================================================================
-- Part 4: Audit Log Query Functions
-- ============================================================================

-- Function to get recent audit logs
CREATE OR REPLACE FUNCTION get_recent_audit_logs(
    limit_count INTEGER DEFAULT 100,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    id INTEGER,
    table_name VARCHAR,
    record_id INTEGER,
    operation VARCHAR,
    changed_at TIMESTAMP,
    changed_by VARCHAR,
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        al.id,
        al.table_name,
        al.record_id,
        al.operation,
        al.changed_at,
        al.changed_by,
        al.old_values,
        al.new_values,
        al.changed_fields
    FROM audit_log al
    ORDER BY al.changed_at DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get audit logs for a specific record
CREATE OR REPLACE FUNCTION get_record_audit_history(
    p_table_name VARCHAR,
    p_record_id INTEGER
)
RETURNS TABLE (
    id INTEGER,
    operation VARCHAR,
    changed_at TIMESTAMP,
    changed_by VARCHAR,
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        al.id,
        al.operation,
        al.changed_at,
        al.changed_by,
        al.old_values,
        al.new_values,
        al.changed_fields
    FROM audit_log al
    WHERE al.table_name = p_table_name
    AND al.record_id = p_record_id
    ORDER BY al.changed_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to get audit logs by user
CREATE OR REPLACE FUNCTION get_user_audit_logs(
    p_user_email VARCHAR,
    limit_count INTEGER DEFAULT 100
)
RETURNS TABLE (
    id INTEGER,
    table_name VARCHAR,
    record_id INTEGER,
    operation VARCHAR,
    changed_at TIMESTAMP,
    old_values JSONB,
    new_values JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        al.id,
        al.table_name,
        al.record_id,
        al.operation,
        al.changed_at,
        al.old_values,
        al.new_values
    FROM audit_log al
    WHERE al.changed_by = p_user_email
    ORDER BY al.changed_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Part 5: Audit Log Maintenance
-- ============================================================================

-- Function to archive old audit logs (keeps last 90 days by default)
CREATE OR REPLACE FUNCTION archive_old_audit_logs(
    retention_days INTEGER DEFAULT 90
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_log
    WHERE changed_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Part 6: Audit Statistics Views
-- ============================================================================

-- View for audit statistics by table
CREATE OR REPLACE VIEW audit_stats_by_table AS
SELECT
    table_name,
    COUNT(*) as total_changes,
    COUNT(DISTINCT record_id) as unique_records,
    COUNT(CASE WHEN operation = 'INSERT' THEN 1 END) as inserts,
    COUNT(CASE WHEN operation = 'UPDATE' THEN 1 END) as updates,
    COUNT(CASE WHEN operation = 'DELETE' THEN 1 END) as deletes,
    MIN(changed_at) as first_change,
    MAX(changed_at) as last_change
FROM audit_log
GROUP BY table_name
ORDER BY total_changes DESC;

-- View for audit statistics by user
CREATE OR REPLACE VIEW audit_stats_by_user AS
SELECT
    changed_by,
    COUNT(*) as total_changes,
    COUNT(DISTINCT table_name) as tables_modified,
    COUNT(CASE WHEN operation = 'INSERT' THEN 1 END) as inserts,
    COUNT(CASE WHEN operation = 'UPDATE' THEN 1 END) as updates,
    COUNT(CASE WHEN operation = 'DELETE' THEN 1 END) as deletes,
    MIN(changed_at) as first_change,
    MAX(changed_at) as last_change
FROM audit_log
WHERE changed_by IS NOT NULL
GROUP BY changed_by
ORDER BY total_changes DESC;

-- ============================================================================
-- Migration Complete!
-- ============================================================================

-- Verify audit system is working
DO $$
BEGIN
    RAISE NOTICE '✅ Audit logging system installed successfully!';
    RAISE NOTICE '   - Audit log table created';
    RAISE NOTICE '   - Triggers installed on all tables';
    RAISE NOTICE '   - Query functions available';
    RAISE NOTICE '   - Statistics views created';
END $$;
