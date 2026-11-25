-- =============================================================================
-- Script: Clear Historical Instantaneous Vibration Alerts
-- Target Schema: tiei_sample_4 (or replace with your environment's schema)
-- Purpose: Remove historical warning and critical alert events from corrective_activity
--          that were triggered under the old instantaneous peak logic.
-- =============================================================================

BEGIN;

-- 1. Set the target schema (change if deploying to a different schema)
SET search_path TO tiei_sample_4, public;

-- 2. Remove old vibration alerts for the 56 vibration parameters mapped across machines/ports:
--    - Range 1: 7009 to 7036 (T_C_OP200, T_H_OP120, T_H_OP200, T_H_OP285)
--    - Range 2: 7154 to 7181
DELETE FROM corrective_activity
WHERE machine_parameters_id IN (
    -- Range 1
    7009, 7010, 7011, 7012, 7013, 7014, 7015, 7016, 7017, 7018, 7019, 7020, 7021, 7022,
    7023, 7024, 7025, 7026, 7027, 7028, 7029, 7030, 7031, 7032, 7033, 7034, 7035, 7036,
    -- Range 2
    7154, 7155, 7156, 7157, 7158, 7159, 7160, 7161, 7162, 7163, 7164, 7165, 7166, 7167,
    7168, 7169, 7170, 7171, 7172, 7173, 7174, 7175, 7176, 7177, 7178, 7179, 7180, 7181
);

COMMIT;

-- =============================================================================
-- Verification Query
-- =============================================================================
-- SELECT COUNT(*) 
-- FROM corrective_activity 
-- WHERE machine_parameters_id BETWEEN 7009 AND 7036 
--    OR machine_parameters_id BETWEEN 7154 AND 7181;
