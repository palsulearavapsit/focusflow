-- FocusFlow Database Schema — MySQL 8.0+
-- Run this in MySQL Workbench or CLI: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS focusflow;
USE focusflow;

-- ─── Users Table ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'teacher', 'admin') NOT NULL DEFAULT 'student',
    streak_count INT DEFAULT 0,
    max_streak INT DEFAULT 0,
    last_study_date DATE DEFAULT NULL,
    title VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Classrooms Table ─────────────────────────────────────────────────────────
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

-- ─── Classroom Students Junction ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS classroom_students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classroom_id INT NOT NULL,
    student_id INT NOT NULL,
    role ENUM('student', 'representative') DEFAULT 'student',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_membership (classroom_id, student_id),
    INDEX idx_classroom (classroom_id),
    INDEX idx_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Sessions Table ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    classroom_id INT DEFAULT NULL,
    technique ENUM('pomodoro', '52-17', 'study-sprint', 'flowtime') NOT NULL,
    study_mode ENUM('screen', 'book') NOT NULL,
    camera_enabled BOOLEAN DEFAULT FALSE,
    face_detection_enabled BOOLEAN DEFAULT FALSE,
    emotion_detection_enabled BOOLEAN DEFAULT FALSE,
    duration INT NOT NULL COMMENT 'Duration in seconds',
    distractions INT DEFAULT 0,
    focus_score DECIMAL(5,2) DEFAULT 0.00,
    mouse_inactive_time INT DEFAULT 0,
    keyboard_inactive_time INT DEFAULT 0,
    tab_switches INT DEFAULT 0,
    camera_absence_time INT DEFAULT 0,
    face_absence_time INT DEFAULT 0,
    dominant_emotion VARCHAR(50) DEFAULT 'UNKNOWN',
    emotion_confidence DECIMAL(5,2) DEFAULT 0.00,
    user_state VARCHAR(50) DEFAULT 'focused',
    recommended_technique VARCHAR(50) DEFAULT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_technique (technique),
    INDEX idx_study_mode (study_mode),
    INDEX idx_session_user_timestamp (user_id, timestamp),
    INDEX idx_focus_score (focus_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Auto-Calculate Focus Score (Trigger) ─────────────────────────────────────
DROP TRIGGER IF EXISTS calculate_focus_score_before_insert;

DELIMITER //
CREATE TRIGGER calculate_focus_score_before_insert
BEFORE INSERT ON sessions
FOR EACH ROW
BEGIN
    DECLARE idleRatio DECIMAL(5,4);
    DECLARE distractionPenalty DECIMAL(5,2);
    DECLARE consistencyScore DECIMAL(5,2);
    DECLARE cameraScore DECIMAL(5,2);
    DECLARE totalIdleTime INT;
    DECLARE calculatedScore DECIMAL(5,2);

    SET totalIdleTime = NEW.mouse_inactive_time + NEW.keyboard_inactive_time;
    SET idleRatio = totalIdleTime / NULLIF(NEW.duration, 0);

    -- 40% weight: idle time
    SET calculatedScore = (1 - COALESCE(idleRatio, 0)) * 40;

    -- 30% weight: distractions
    SET distractionPenalty = GREATEST(0, 30 - (NEW.distractions * 3));
    SET calculatedScore = calculatedScore + distractionPenalty;

    -- 20% weight: consistency
    IF NEW.distractions = 0 THEN
        SET consistencyScore = 20;
    ELSE
        SET consistencyScore = GREATEST(0, 20 - (NEW.distractions * 2));
    END IF;
    SET calculatedScore = calculatedScore + consistencyScore;

    -- 10% weight: camera
    IF NEW.camera_enabled THEN
        SET cameraScore = (1 - (NEW.camera_absence_time / NULLIF(NEW.duration, 0))) * 10;
    ELSE
        SET cameraScore = 5;
    END IF;
    SET calculatedScore = calculatedScore + cameraScore;

    -- Clamp 0-100
    SET NEW.focus_score = GREATEST(0, LEAST(100, calculatedScore));

    -- Recommend next technique
    IF NEW.distractions > 5 THEN
        SET NEW.recommended_technique = 'study-sprint';
    ELSEIF NEW.focus_score >= 70 THEN
        SET NEW.recommended_technique = '52-17';
    ELSEIF NEW.focus_score >= 50 THEN
        SET NEW.recommended_technique = 'pomodoro';
    ELSE
        SET NEW.recommended_technique = 'flowtime';
    END IF;
END //
DELIMITER ;

-- ─── Views ────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW admin_dashboard_stats AS
SELECT
    (SELECT COUNT(*) FROM users WHERE role = 'student') AS total_students,
    (SELECT COUNT(*) FROM sessions) AS total_sessions,
    (SELECT AVG(focus_score) FROM sessions) AS overall_avg_focus_score,
    (SELECT COALESCE(SUM(duration), 0) FROM sessions) AS total_study_time_all_users,
    (SELECT COUNT(*) FROM sessions WHERE camera_enabled = TRUE) AS sessions_with_camera_enabled,
    (SELECT technique FROM sessions GROUP BY technique ORDER BY COUNT(*) DESC LIMIT 1) AS most_popular_technique,
    (SELECT study_mode FROM sessions GROUP BY study_mode ORDER BY COUNT(*) DESC LIMIT 1) AS most_popular_mode;

-- ─── Default Admin User ───────────────────────────────────────────────────────
-- Password: admin123 (bcrypt hash)
INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@focusflow.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/qvQu6', 'admin')
ON DUPLICATE KEY UPDATE username=username;

-- ─── Group Sessions Table ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS group_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    meeting_code VARCHAR(10) NOT NULL UNIQUE,
    host_id INT NOT NULL,
    status ENUM('active', 'ended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (host_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_meeting_code (meeting_code),
    INDEX idx_host_id (host_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Group Session Participants Table ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS group_session_participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_session_id INT NOT NULL,
    user_id INT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_session_id) REFERENCES group_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_p_membership (group_session_id, user_id),
    INDEX idx_group_session (group_session_id),
    INDEX idx_p_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
