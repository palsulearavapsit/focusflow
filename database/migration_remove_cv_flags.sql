-- Database Migration: Remove individual CV feature flags
-- 
-- Changes:
-- - Remove face_detection_enabled column from sessions table
-- - Remove emotion_detection_enabled column from sessions table
-- 
-- Reason: Simplified to single camera_enabled flag
-- When camera_enabled=True, all CV features (face detection, eye tracking, emotion detection) run automatically
--
-- Run this migration if your database already has these columns
-- If starting fresh, these columns won't exist

-- Remove face_detection_enabled column
ALTER TABLE sessions DROP COLUMN IF EXISTS face_detection_enabled;

-- Remove emotion_detection_enabled column
ALTER TABLE sessions DROP COLUMN IF EXISTS emotion_detection_enabled;

-- Add comment to camera_enabled column for clarity
ALTER TABLE sessions MODIFY COLUMN camera_enabled BOOLEAN DEFAULT FALSE 
    COMMENT 'When TRUE, all CV features (face, eye, emotion detection) are enabled';

-- Migration complete
SELECT 'Migration completed: Removed face_detection_enabled and emotion_detection_enabled columns' AS status;
