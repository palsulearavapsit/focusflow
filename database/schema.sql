-- FocusFlow Database Schema
-- MySQL 8.0+

-- Create database
CREATE DATABASE IF NOT EXISTS focusflow;
USE focusflow;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'admin') NOT NULL DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Study sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    technique ENUM('pomodoro', '52-17', 'study-sprint', 'flowtime') NOT NULL,
    study_mode ENUM('screen', 'book') NOT NULL,
    camera_enabled BOOLEAN DEFAULT FALSE,
    face_detection_enabled BOOLEAN DEFAULT FALSE COMMENT 'Phase-2: Will be used when face detection is integrated',
    emotion_detection_enabled BOOLEAN DEFAULT FALSE COMMENT 'Phase-2: Will be used when emotion detection is integrated',
    duration INT NOT NULL COMMENT 'Duration in seconds',
    distractions INT DEFAULT 0,
    focus_score DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Score from 0 to 100',
    mouse_inactive_time INT DEFAULT 0 COMMENT 'Total mouse inactive time in seconds',
    keyboard_inactive_time INT DEFAULT 0 COMMENT 'Total keyboard inactive time in seconds',
    tab_switches INT DEFAULT 0,
    camera_absence_time INT DEFAULT 0 COMMENT 'Total camera absence time in seconds',
    face_absence_time INT DEFAULT 0 COMMENT 'Phase-2: Will track face absence duration',
    dominant_emotion VARCHAR(50) DEFAULT 'UNKNOWN' COMMENT 'Phase-2: Will store detected emotion',
    emotion_confidence DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Phase-2: Emotion detection confidence',
    user_state VARCHAR(50) DEFAULT 'focused' COMMENT 'focused, reading, distracted, away',
    recommended_technique VARCHAR(50) COMMENT 'AI-recommended technique for next session',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_technique (technique),
    INDEX idx_study_mode (study_mode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Classrooms table
CREATE TABLE IF NOT EXISTS classrooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) NOT NULL UNIQUE,
    teacher_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_code (code),
    INDEX idx_teacher (teacher_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Classroom Students junction table
CREATE TABLE IF NOT EXISTS classroom_students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classroom_id INT NOT NULL,
    student_id INT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_membership (classroom_id, student_id),
    INDEX idx_classroom (classroom_id),
    INDEX idx_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Study sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    classroom_id INT DEFAULT NULL,
    technique ENUM('pomodoro', '52-17', 'study-sprint', 'flowtime') NOT NULL,
    study_mode ENUM('screen', 'book') NOT NULL,
    camera_enabled BOOLEAN DEFAULT FALSE,
    face_detection_enabled BOOLEAN DEFAULT FALSE COMMENT 'Phase-2: Will be used when face detection is integrated',
    emotion_detection_enabled BOOLEAN DEFAULT FALSE COMMENT 'Phase-2: Will be used when emotion detection is integrated',
    duration INT NOT NULL COMMENT 'Duration in seconds',
    distractions INT DEFAULT 0,
    focus_score DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Score from 0 to 100',
    mouse_inactive_time INT DEFAULT 0 COMMENT 'Total mouse inactive time in seconds',
    keyboard_inactive_time INT DEFAULT 0 COMMENT 'Total keyboard inactive time in seconds',
    tab_switches INT DEFAULT 0,
    camera_absence_time INT DEFAULT 0 COMMENT 'Total camera absence time in seconds',
    face_absence_time INT DEFAULT 0 COMMENT 'Phase-2: Will track face absence duration',
    dominant_emotion VARCHAR(50) DEFAULT 'UNKNOWN' COMMENT 'Phase-2: Will store detected emotion',
    emotion_confidence DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Phase-2: Emotion detection confidence',
    user_state VARCHAR(50) DEFAULT 'focused' COMMENT 'focused, reading, distracted, away',
    recommended_technique VARCHAR(50) COMMENT 'AI-recommended technique for next session',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_technique (technique),
    INDEX idx_study_mode (study_mode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default admin user
-- Password: admin123 (hashed with bcrypt)
-- Note: This hash is for 'admin123' - you should change this in production
INSERT INTO users (username, email, password_hash, role) VALUES 
('admin', 'admin@focusflow.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/qvQu6', 'admin')
ON DUPLICATE KEY UPDATE username=username;

-- Insert test student user
-- Password: student123 (hashed with bcrypt)
INSERT INTO users (username, email, password_hash, role) VALUES 
('student', 'student@test.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/qvQu6', 'student')
ON DUPLICATE KEY UPDATE username=username;

-- Create view for session statistics
CREATE OR REPLACE VIEW session_statistics AS
SELECT 
    u.id as user_id,
    u.username,
    u.email,
    COUNT(s.id) as total_sessions,
    SUM(s.duration) as total_study_time,
    AVG(s.focus_score) as avg_focus_score,
    SUM(s.distractions) as total_distractions,
    AVG(s.distractions) as avg_distractions_per_session,
    s.technique as most_used_technique,
    COUNT(CASE WHEN s.camera_enabled = TRUE THEN 1 END) as sessions_with_camera
FROM users u
LEFT JOIN sessions s ON u.id = s.user_id
WHERE u.role = 'student'
GROUP BY u.id, u.username, u.email, s.technique;

-- Create view for admin dashboard
CREATE OR REPLACE VIEW admin_dashboard_stats AS
SELECT 
    (SELECT COUNT(*) FROM users WHERE role = 'student') as total_students,
    (SELECT COUNT(*) FROM sessions) as total_sessions,
    (SELECT AVG(focus_score) FROM sessions) as overall_avg_focus_score,
    (SELECT SUM(duration) FROM sessions) as total_study_time_all_users,
    (SELECT COUNT(*) FROM sessions WHERE camera_enabled = TRUE) as sessions_with_camera_enabled,
    (SELECT technique FROM sessions GROUP BY technique ORDER BY COUNT(*) DESC LIMIT 1) as most_popular_technique,
    (SELECT study_mode FROM sessions GROUP BY study_mode ORDER BY COUNT(*) DESC LIMIT 1) as most_popular_mode;

-- Stored procedure to get user session history
DELIMITER //
CREATE PROCEDURE GetUserSessionHistory(IN userId INT, IN limitCount INT)
BEGIN
    SELECT 
        id,
        technique,
        study_mode,
        camera_enabled,
        face_detection_enabled,
        emotion_detection_enabled,
        duration,
        distractions,
        focus_score,
        user_state,
        dominant_emotion,
        recommended_technique,
        timestamp
    FROM sessions
    WHERE user_id = userId
    ORDER BY timestamp DESC
    LIMIT limitCount;
END //
DELIMITER ;

-- Stored procedure to calculate focus score
DELIMITER //
CREATE PROCEDURE CalculateFocusScore(
    IN sessionDuration INT,
    IN totalIdleTime INT,
    IN distractionCount INT,
    IN cameraEnabled BOOLEAN,
    IN cameraAbsenceTime INT,
    OUT focusScore DECIMAL(5,2)
)
BEGIN
    DECLARE idleRatio DECIMAL(5,4);
    DECLARE distractionPenalty DECIMAL(5,2);
    DECLARE consistencyScore DECIMAL(5,2);
    DECLARE cameraScore DECIMAL(5,2);
    
    -- Calculate idle ratio (0-1)
    SET idleRatio = totalIdleTime / sessionDuration;
    
    -- Idle time component (40% weight) - lower is better
    SET focusScore = (1 - idleRatio) * 40;
    
    -- Distraction penalty (30% weight)
    SET distractionPenalty = GREATEST(0, 30 - (distractionCount * 3));
    SET focusScore = focusScore + distractionPenalty;
    
    -- Consistency score (20% weight) - based on distraction frequency
    IF distractionCount = 0 THEN
        SET consistencyScore = 20;
    ELSE
        SET consistencyScore = GREATEST(0, 20 - (distractionCount * 2));
    END IF;
    SET focusScore = focusScore + consistencyScore;
    
    -- Camera availability (10% weight)
    IF cameraEnabled THEN
        SET cameraScore = (1 - (cameraAbsenceTime / sessionDuration)) * 10;
    ELSE
        SET cameraScore = 5; -- Neutral score if camera not used
    END IF;
    SET focusScore = focusScore + cameraScore;
    
    -- Ensure score is between 0 and 100
    SET focusScore = GREATEST(0, LEAST(100, focusScore));
END //
DELIMITER ;

-- Function to recommend next technique
DELIMITER //
CREATE FUNCTION RecommendTechnique(
    avgDistractions DECIMAL(5,2),
    avgFocusScore DECIMAL(5,2)
) RETURNS VARCHAR(50)
DETERMINISTIC
BEGIN
    DECLARE recommendation VARCHAR(50);
    
    IF avgDistractions > 5 THEN
        SET recommendation = 'study-sprint';
    ELSEIF avgFocusScore >= 70 THEN
        SET recommendation = '52-17';
    ELSEIF avgFocusScore >= 50 THEN
        SET recommendation = 'pomodoro';
    ELSE
        SET recommendation = 'flowtime';
    END IF;
    
    RETURN recommendation;
END //
DELIMITER ;

-- Trigger to auto-calculate focus score before insert
DELIMITER //
CREATE TRIGGER calculate_focus_score_before_insert
BEFORE INSERT ON sessions
FOR EACH ROW
BEGIN
    DECLARE calculatedScore DECIMAL(5,2);
    DECLARE totalIdleTime INT;
    
    SET totalIdleTime = NEW.mouse_inactive_time + NEW.keyboard_inactive_time;
    
    CALL CalculateFocusScore(
        NEW.duration,
        totalIdleTime,
        NEW.distractions,
        NEW.camera_enabled,
        NEW.camera_absence_time,
        calculatedScore
    );
    
    SET NEW.focus_score = calculatedScore;
    
    -- Auto-recommend technique for next session
    SET NEW.recommended_technique = RecommendTechnique(NEW.distractions, calculatedScore);
END //
DELIMITER ;

-- Create indexes for performance
CREATE INDEX idx_session_user_timestamp ON sessions(user_id, timestamp);
CREATE INDEX idx_session_focus_score ON sessions(focus_score);
CREATE INDEX idx_session_technique_mode ON sessions(technique, study_mode);

-- Comments for Phase-2 integration
-- The following columns are ready for Phase-2 ML integration:
-- - face_detection_enabled: Toggle for face detection feature
-- - emotion_detection_enabled: Toggle for emotion detection feature
-- - face_absence_time: Will track duration when face is not detected
-- - dominant_emotion: Will store the most frequent emotion during session
-- - emotion_confidence: Will store average confidence of emotion detection
-- 
-- Pre-trained models will be integrated in Phase-2:
-- - Face Detection: MediaPipe Face Detection / Face-API.js
-- - Emotion Detection: Pre-trained CNN model for emotion classification
-- 
-- No custom ML training required - only pre-trained model integration
