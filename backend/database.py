"""
FocusFlow MySQL Database Module
Uses SQLAlchemy + mysql-connector-python
"""

import mysql.connector
from mysql.connector import Error
from typing import Optional, List, Dict, Any
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection():
    """Get a new MySQL connection"""
    return mysql.connector.connect(
        host=settings.DB_HOST,
        port=int(settings.DB_PORT),
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset='utf8mb4'
    )


class Database:
    """MySQL wrapper for FocusFlow"""

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = get_connection()
            conn.close()
            logger.info("✅ MySQL connection OK")
            return True
        except Exception as e:
            logger.error(f"❌ MySQL connection failed: {e}")
            return False


# Global database instance
db = Database()


# ─── Helper Functions ────────────────────────────────────────────────────────

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def get_user_by_username(username: str) -> Optional[Dict]:
    """Get user by username"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def create_user(username: str, email: str, password_hash: str, role: str = "student") -> Dict:
    """Create a new user"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (username, email, password_hash, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return get_user_by_id(user_id)
    finally:
        cursor.close(); conn.close()


def create_session(session_data: Dict) -> Dict:
    """Create a new study session (focus_score calculated by MySQL trigger)"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            INSERT INTO sessions
            (user_id, technique, study_mode, camera_enabled, face_detection_enabled,
             emotion_detection_enabled, classroom_id, duration, distractions,
             mouse_inactive_time, keyboard_inactive_time, tab_switches,
             camera_absence_time, face_absence_time, dominant_emotion,
             emotion_confidence, user_state)
            VALUES
            (%(user_id)s, %(technique)s, %(study_mode)s, %(camera_enabled)s,
             %(face_detection_enabled)s, %(emotion_detection_enabled)s,
             %(classroom_id)s, %(duration)s, %(distractions)s,
             %(mouse_inactive_time)s, %(keyboard_inactive_time)s, %(tab_switches)s,
             %(camera_absence_time)s, %(face_absence_time)s, %(dominant_emotion)s,
             %(emotion_confidence)s, %(user_state)s)
        """
        cursor.execute(sql, session_data)
        conn.commit()
        session_id = cursor.lastrowid
        # Fetch back the saved session (includes trigger-calculated focus_score)
        cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def update_session_focus_score(session_id: int, focus_score: float):
    """Update a session's focus score"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET focus_score = %s WHERE id = %s",
            (focus_score, session_id)
        )
        conn.commit()
    finally:
        cursor.close(); conn.close()


def get_user_sessions(user_id: int, limit: int = 10) -> List[Dict]:
    """Get user's session history"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM sessions WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s",
            (user_id, limit)
        )
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def get_admin_statistics() -> Dict:
    """Get aggregated platform statistics"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM users WHERE role = 'student') AS total_students,
                (SELECT COUNT(*) FROM sessions) AS total_sessions,
                (SELECT AVG(focus_score) FROM sessions) AS overall_avg_focus_score,
                (SELECT COALESCE(SUM(duration), 0) FROM sessions) AS total_study_time_all_users,
                (SELECT COUNT(*) FROM sessions WHERE camera_enabled = TRUE) AS sessions_with_camera_enabled,
                (SELECT technique FROM sessions GROUP BY technique ORDER BY COUNT(*) DESC LIMIT 1) AS most_popular_technique,
                (SELECT study_mode FROM sessions GROUP BY study_mode ORDER BY COUNT(*) DESC LIMIT 1) AS most_popular_mode
        """)
        row = cursor.fetchone()
        # Ensure numeric nulls become 0
        row['total_students'] = row['total_students'] or 0
        row['total_sessions'] = row['total_sessions'] or 0
        row['total_study_time_all_users'] = row['total_study_time_all_users'] or 0
        row['sessions_with_camera_enabled'] = row['sessions_with_camera_enabled'] or 0
        row['overall_avg_focus_score'] = float(row['overall_avg_focus_score']) if row['overall_avg_focus_score'] else None
        return row
    finally:
        cursor.close(); conn.close()


def get_all_users() -> List[Dict]:
    """Get all users"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, email, role, streak_count, max_streak, title, created_at FROM users")
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def delete_user(user_id: int):
    """Delete a user"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    finally:
        cursor.close(); conn.close()


def get_all_sessions(limit: int = 50) -> List[Dict]:
    """Get all sessions with user info"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, u.username, u.email
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.timestamp DESC
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()

def get_all_user_statistics() -> List[Dict]:
    """Get aggregated statistics for all users for admin dashboard"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                u.id AS user_id, 
                u.username, 
                COUNT(s.id) AS total_sessions,
                COALESCE(SUM(s.duration), 0) AS total_study_time,
                COALESCE(AVG(s.focus_score), 0) AS avg_focus_score,
                COALESCE(SUM(s.distractions), 0) AS total_distractions,
                (SELECT technique FROM sessions WHERE user_id = u.id GROUP BY technique ORDER BY COUNT(*) DESC LIMIT 1) AS most_used_technique,
                COUNT(CASE WHEN s.camera_enabled = TRUE THEN 1 END) AS sessions_with_camera
            FROM users u
            LEFT JOIN sessions s ON u.id = s.user_id
            GROUP BY u.id, u.username
        """)
        rows = cursor.fetchall()
        for row in rows:
            row['avg_focus_score'] = float(row['avg_focus_score']) if row['avg_focus_score'] else 0.0
            row['total_study_time'] = int(row['total_study_time'])
            row['total_sessions'] = int(row['total_sessions'])
            row['total_distractions'] = int(row['total_distractions'])
        return rows
    finally:
        cursor.close(); conn.close()


def update_user_system_role(user_id: int, role: str):
    """Update user's system role (student, teacher, admin)"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
        conn.commit()
    finally:
        cursor.close(); conn.close()


def create_classroom(name: str, code: str, teacher_id: int) -> Dict:
    """Create a new classroom"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "INSERT INTO classrooms (name, code, teacher_id) VALUES (%s, %s, %s)",
            (name, code, teacher_id)
        )
        conn.commit()
        classroom_id = cursor.lastrowid
        cursor.execute("SELECT * FROM classrooms WHERE id = %s", (classroom_id,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def get_classroom_by_code(code: str) -> Optional[Dict]:
    """Get classroom by code"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM classrooms WHERE code = %s", (code,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def add_student_to_classroom(classroom_id: int, student_id: int):
    """Enroll student in classroom"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO classroom_students (classroom_id, student_id) VALUES (%s, %s)",
            (classroom_id, student_id)
        )
        conn.commit()
    finally:
        cursor.close(); conn.close()


def get_teacher_classrooms(teacher_id: int) -> List[Dict]:
    """Get classrooms created by teacher with student count"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, COUNT(cs.student_id) AS student_count
            FROM classrooms c
            LEFT JOIN classroom_students cs ON c.id = cs.classroom_id
            WHERE c.teacher_id = %s
            GROUP BY c.id
        """, (teacher_id,))
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def get_classroom_detail(classroom_id: int) -> Optional[Dict]:
    """Get classroom info + per-student session stats for the teacher dashboard page"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        # Basic classroom info
        cursor.execute("SELECT * FROM classrooms WHERE id = %s", (classroom_id,))
        classroom = cursor.fetchone()
        if not classroom:
            return None

        # Students with aggregated stats
        cursor.execute("""
            SELECT
                u.id AS student_id,
                u.username,
                u.email,
                cs.role,
                COUNT(s.id)                     AS total_sessions,
                COALESCE(SUM(s.duration), 0)    AS total_study_time,
                COALESCE(AVG(s.focus_score), 0) AS avg_focus_score
            FROM classroom_students cs
            JOIN users u ON cs.student_id = u.id
            LEFT JOIN sessions s
                ON s.user_id = cs.student_id AND s.classroom_id = %s
            WHERE cs.classroom_id = %s
            GROUP BY u.id, u.username, u.email, cs.role
            ORDER BY avg_focus_score DESC
        """, (classroom_id, classroom_id))
        students = cursor.fetchall()

        return {"classroom": classroom, "students": students}
    finally:
        cursor.close(); conn.close()


def remove_student_from_classroom(classroom_id: int, student_id: int):
    """Remove a student from a classroom"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM classroom_students WHERE classroom_id = %s AND student_id = %s",
            (classroom_id, student_id)
        )
        conn.commit()
    finally:
        cursor.close(); conn.close()


def update_student_role_in_classroom(classroom_id: int, student_id: int, role: str):
    """Update a student's role in a classroom"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE classroom_students SET role = %s WHERE classroom_id = %s AND student_id = %s",
            (role, classroom_id, student_id)
        )
        conn.commit()
    finally:
        cursor.close(); conn.close()


def get_student_classroom_sessions(classroom_id: int, student_id: int) -> List[Dict]:
    """Get all sessions of a student within a specific classroom"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM sessions WHERE classroom_id = %s AND user_id = %s ORDER BY timestamp DESC",
            (classroom_id, student_id)
        )
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def get_student_classrooms(student_id: int) -> List[Dict]:
    """Get classrooms a student has joined"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, COUNT(cs2.student_id) AS student_count
            FROM classroom_students cs
            JOIN classrooms c ON cs.classroom_id = c.id
            LEFT JOIN classroom_students cs2 ON c.id = cs2.classroom_id
            WHERE cs.student_id = %s
            GROUP BY c.id
        """, (student_id,))
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def get_all_classrooms() -> List[Dict]:
    """Get all classrooms (admin)"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, u.username AS teacher_name, COUNT(cs.student_id) AS student_count
            FROM classrooms c
            JOIN users u ON c.teacher_id = u.id
            LEFT JOIN classroom_students cs ON c.id = cs.classroom_id
            GROUP BY c.id
        """)
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def get_classroom_sessions(classroom_id: int, user_id: Optional[int] = None) -> List[Dict]:
    """Get sessions for a classroom (optionally filtered by student)"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if user_id:
            cursor.execute(
                "SELECT * FROM sessions WHERE classroom_id = %s AND user_id = %s ORDER BY timestamp DESC",
                (classroom_id, user_id)
            )
        else:
            cursor.execute(
                "SELECT * FROM sessions WHERE classroom_id = %s ORDER BY timestamp DESC",
                (classroom_id,)
            )
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def get_teacher_students(teacher_id: int) -> List[Dict]:
    """Get all distinct students in teacher's classrooms with their class names"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                u.id, 
                u.username, 
                u.email, 
                u.role, 
                u.streak_count, 
                u.title,
                GROUP_CONCAT(c.name SEPARATOR ', ') AS enrolled_classes
            FROM classroom_students cs
            JOIN classrooms c ON cs.classroom_id = c.id
            JOIN users u ON cs.student_id = u.id
            WHERE c.teacher_id = %s
            GROUP BY u.id, u.username, u.email, u.role, u.streak_count, u.title
        """, (teacher_id,))
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def delete_classroom(classroom_id: int):
    """Delete a classroom (cascades happen in DB)"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM classrooms WHERE id = %s", (classroom_id,))
        conn.commit()
    finally:
        cursor.close(); conn.close()


def update_user_streak(user_id: int):
    """Update user streak based on study activity"""
    from datetime import date
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT last_study_date, streak_count, max_streak FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return

        today = date.today()
        last_date = user.get('last_study_date')
        streak = user.get('streak_count', 0)
        max_streak = user.get('max_streak', 0)

        if last_date is None or (today - last_date).days > 1:
            streak = 1  # Reset
        elif (today - last_date).days == 1:
            streak += 1  # Consecutive day

        max_streak = max(max_streak, streak)

        cursor.execute(
            "UPDATE users SET last_study_date = %s, streak_count = %s, max_streak = %s WHERE id = %s",
            (today, streak, max_streak, user_id)
        )
        conn.commit()
    finally:
        cursor.close(); conn.close()


def update_user_title(user_id: int, title: str):
    """Update user's display title"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET title = %s WHERE id = %s", (title, user_id))
        conn.commit()
    finally:
        cursor.close(); conn.close()


# ─── Discussion Forum / Chat Functions ──────────────────────────────────────

def get_chat_contacts(user_id: int, role: str) -> List[Dict]:
    """Get list of users this person can chat with based on their role.
    Students: see classmates + their teachers.
    Teachers: see their students.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if role == 'student':
            # Get classmates and teachers from joined classrooms
            cursor.execute("""
                SELECT DISTINCT u.id, u.username, u.role
                FROM users u
                WHERE u.id != %s
                  AND (
                    -- Teachers of the student's classrooms
                    u.id IN (
                        SELECT c.teacher_id
                        FROM classroom_students cs
                        JOIN classrooms c ON cs.classroom_id = c.id
                        WHERE cs.student_id = %s
                    )
                    OR
                    -- Classmates in the same classrooms
                    u.id IN (
                        SELECT cs2.student_id
                        FROM classroom_students cs
                        JOIN classroom_students cs2 ON cs.classroom_id = cs2.classroom_id
                        WHERE cs.student_id = %s AND cs2.student_id != %s
                    )
                  )
                ORDER BY u.role DESC, u.username ASC
            """, (user_id, user_id, user_id, user_id))
        else:
            # Teacher: see all their students
            cursor.execute("""
                SELECT DISTINCT u.id, u.username, u.role
                FROM users u
                JOIN classroom_students cs ON u.id = cs.student_id
                JOIN classrooms c ON cs.classroom_id = c.id
                WHERE c.teacher_id = %s
                ORDER BY u.username ASC
            """, (user_id,))
        contacts = cursor.fetchall()
        # Add unread count per contact
        for contact in contacts:
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM chat_messages
                WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
            """, (contact['id'], user_id))
            row = cursor.fetchone()
            contact['unread_count'] = row['cnt'] if row else 0
        return contacts
    finally:
        cursor.close(); conn.close()


def get_chat_history(user_id: int, contact_id: int) -> List[Dict]:
    """Get private message history between user_id and contact_id.
    PRIVACY ENFORCED: Only messages where current user is sender OR receiver
    are returned. No other user's messages can bleed through.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                m.id,
                m.sender_id,
                m.receiver_id,
                m.content,
                m.is_read,
                m.created_at,
                u.username AS sender_name
            FROM chat_messages m
            JOIN users u ON m.sender_id = u.id
            WHERE
                (m.sender_id = %s AND m.receiver_id = %s)
                OR
                (m.sender_id = %s AND m.receiver_id = %s)
            ORDER BY m.created_at ASC
        """, (user_id, contact_id, contact_id, user_id))
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def send_chat_message(sender_id: int, receiver_id: int, content: str) -> Dict:
    """Save a new chat message to the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "INSERT INTO chat_messages (sender_id, receiver_id, content) VALUES (%s, %s, %s)",
            (sender_id, receiver_id, content)
        )
        conn.commit()
        msg_id = cursor.lastrowid
        cursor.execute("""
            SELECT m.*, u.username AS sender_name
            FROM chat_messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.id = %s
        """, (msg_id,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def get_unread_count(user_id: int) -> int:
    """Get total unread messages for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE receiver_id = %s AND is_read = FALSE",
            (user_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        cursor.close(); conn.close()


def mark_messages_read(receiver_id: int, sender_id: int):
    """Mark all messages from sender_id to receiver_id as read."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_messages SET is_read = TRUE WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE",
            (sender_id, receiver_id)
        )
        conn.commit()
    finally:
        cursor.close(); conn.close()
# ─── Group Session / Meeting Functions ──────────────────────────────────────

def create_group_session(host_id: int, meeting_code: str) -> Dict:
    """Create a new group session with a unique code"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "INSERT INTO group_sessions (meeting_code, host_id) VALUES (%s, %s)",
            (meeting_code, host_id)
        )
        conn.commit()
        session_id = cursor.lastrowid
        cursor.execute("SELECT * FROM group_sessions WHERE id = %s", (session_id,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def get_group_session_by_code(code: str) -> Optional[Dict]:
    """Get active group session by its 6-letter code"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM group_sessions WHERE meeting_code = %s AND status = 'active'", 
            (code,)
        )
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def add_participant_to_group(group_session_id: int, user_id: int):
    """Add a user to a group session's participant list"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO group_session_participants (group_session_id, user_id) VALUES (%s, %s)",
            (group_session_id, user_id)
        )
        conn.commit()
    finally:
        cursor.close(); conn.close()


def get_group_participants(group_session_id: int) -> List[Dict]:
    """Get list of all users currently in the group session"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.id, u.username, u.role, u.title, p.joined_at
            FROM group_session_participants p
            JOIN users u ON p.user_id = u.id
            WHERE p.group_session_id = %s
            ORDER BY p.joined_at ASC
        """, (group_session_id,))
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()


def end_group_session(group_session_id: int):
    """Mark a group session as ended"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE group_sessions SET status = 'ended' WHERE id = %s",
            (group_session_id,)
        )
        conn.commit()
    finally:
        cursor.close(); conn.close()


# ─── Group Chat Functions ────────────────────────────────────────────────────

def send_group_message(group_session_id: int, sender_id: int, content: str) -> Dict:
    """Save a new message for a group session"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "INSERT INTO group_messages (group_session_id, sender_id, content) VALUES (%s, %s, %s)",
            (group_session_id, sender_id, content)
        )
        conn.commit()
        msg_id = cursor.lastrowid
        cursor.execute("""
            SELECT m.*, u.username AS sender_name
            FROM group_messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.id = %s
        """, (msg_id,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


def get_group_messages_db(group_session_id: int, limit: int = 50) -> List[Dict]:
    """Get recent messages for a group session"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.*, u.username AS sender_name
            FROM group_messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.group_session_id = %s
            ORDER BY m.created_at ASC
            LIMIT %s
        """, (group_session_id, limit))
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()
