-- =============================================================================
-- Migration: Add Port & 7 Cycle RMS Parameters to vibration_machine_logs
-- Target Schema: tiei_sample_4 (or replace with your environment's schema)
-- Note: Existing historical rows remain unchanged (RMS columns will be NULL)
-- =============================================================================

BEGIN;

-- 1. Set the target schema (change if deploying to a different schema)
SET search_path TO tiei_sample_4, public;

-- 2. Ensure vibration_machine_logs table exists
CREATE TABLE IF NOT EXISTS vibration_machine_logs (
    id SERIAL PRIMARY KEY,
    machine_id INTEGER REFERENCES vibration_machines(id),
    program_file_id INTEGER,
    program_file_time TIMESTAMPTZ,
    baseline BOOLEAN DEFAULT FALSE
);

-- 3. Add port and the 7 cycle RMS parameter columns to vibration_machine_logs
-- Newly added columns for existing past rows will default to NULL as intended.
ALTER TABLE vibration_machine_logs
    ADD COLUMN IF NOT EXISTS port VARCHAR(50),
    ADD COLUMN IF NOT EXISTS contact_temperature DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS v_peak_x DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS v_peak_y DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS v_peak_z DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS v_rms_x DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS v_rms_y DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS v_rms_z DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS baseline BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS cycle_time DOUBLE PRECISION;

-- 4. Create helpful indexes for performance on vibration_machine_logs
CREATE INDEX IF NOT EXISTS idx_vibration_machine_logs_time 
    ON vibration_machine_logs (machine_id, program_file_time);

CREATE INDEX IF NOT EXISTS idx_vibration_machine_logs_port 
    ON vibration_machine_logs (machine_id, port, program_file_time);

COMMIT;

-- =============================================================================
-- Verification Query
-- =============================================================================
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'vibration_machine_logs'
-- ORDER BY ordinal_position;
