"""
FocusFlow Database Connection Module
Handles MySQL database connections and session management
"""

import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional
from config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """Database connection manager with connection pooling"""
    
    def __init__(self):
        """Initialize database connection pool"""
        self.pool = None
        self._create_pool()
    
    def _create_pool(self):
        """Create MySQL connection pool"""
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="focusflow_pool",
                pool_size=5,
                pool_reset_session=True,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            logger.info("✅ Database connection pool created successfully")
        except Error as e:
            logger.error(f"❌ Error creating connection pool: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            connection = self.pool.get_connection()
            return connection
        except Error as e:
            logger.error(f"❌ Error getting connection from pool: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        """
        Execute a database query
        
        Args:
            query: SQL query string
            params: Query parameters (tuple)
            fetch: Whether to fetch results (SELECT queries)
        
        Returns:
            Query results if fetch=True, else None
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                result = cursor.fetchall()
                return result
            else:
                connection.commit()
                return cursor.lastrowid
                
        except Error as e:
            logger.error(f"❌ Database error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def execute_many(self, query: str, data: list):
        """
        Execute multiple queries (batch insert/update)
        
        Args:
            query: SQL query string
            data: List of tuples containing query parameters
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.executemany(query, data)
            connection.commit()
            logger.info(f"✅ Batch operation successful: {cursor.rowcount} rows affected")
        except Error as e:
            logger.error(f"❌ Batch operation error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def call_procedure(self, proc_name: str, args: tuple = ()):
        """
        Call a stored procedure
        
        Args:
            proc_name: Name of the stored procedure
            args: Procedure arguments
        
        Returns:
            Procedure results
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.callproc(proc_name, args)
            
            results = []
            for result in cursor.stored_results():
                results.extend(result.fetchall())
            
            connection.commit()
            return results
        except Error as e:
            logger.error(f"❌ Stored procedure error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            connection.close()
            logger.info("✅ Database connection test successful")
            return True
        except Error as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False


# Global database instance
db = Database()


# Database helper functions
def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email address"""
    query = "SELECT * FROM users WHERE email = %s"
    result = db.execute_query(query, (email,), fetch=True)
    return result[0] if result else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID"""
    query = "SELECT * FROM users WHERE id = %s"
    result = db.execute_query(query, (user_id,), fetch=True)
    return result[0] if result else None


def create_user(username: str, email: str, password_hash: str, role: str = "student") -> int:
    """Create a new user"""
    query = """
        INSERT INTO users (username, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
    """
    return db.execute_query(query, (username, email, password_hash, role))


def create_session(session_data: dict) -> int:
    """
    Create a new study session
    
    Note: When camera_enabled=True, all CV features (face detection,
    eye tracking, emotion detection) are automatically enabled.
    """
    query = """
        INSERT INTO sessions (
            user_id, classroom_id, technique, study_mode, camera_enabled,
            duration, distractions, mouse_inactive_time,
            keyboard_inactive_time, tab_switches, camera_absence_time,
            face_absence_time, dominant_emotion, emotion_confidence,
            user_state
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    params = (
        session_data.get('user_id'),
        session_data.get('classroom_id'),
        session_data.get('technique'),
        session_data.get('study_mode'),
        session_data.get('camera_enabled', False),
        session_data.get('duration', 0),
        session_data.get('distractions', 0),
        session_data.get('mouse_inactive_time', 0),
        session_data.get('keyboard_inactive_time', 0),
        session_data.get('tab_switches', 0),
        session_data.get('camera_absence_time', 0),
        session_data.get('face_absence_time', 0),
        session_data.get('dominant_emotion', 'UNKNOWN'),
        session_data.get('emotion_confidence', 0.0),
        session_data.get('user_state', 'focused')
    )
    return db.execute_query(query, params)


def update_session_score(session_id: int, focus_score: float):
    """Update session focus score (overriding trigger calculation)"""
    query = "UPDATE sessions SET focus_score = %s WHERE id = %s"
    db.execute_query(query, (focus_score, session_id))


def get_user_sessions(user_id: int, limit: int = 10) -> list:
    """Get user's session history"""
    query = """
        SELECT 
            id, user_id, technique, study_mode, camera_enabled,
            duration, distractions, focus_score, user_state,
            dominant_emotion, emotion_confidence, recommended_technique, timestamp,
            mouse_inactive_time, keyboard_inactive_time, tab_switches,
            camera_absence_time, face_absence_time
        FROM sessions
        WHERE user_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """
    return db.execute_query(query, (user_id, limit), fetch=True)


def get_all_users() -> list:
    """Get all users (admin only)"""
    query = "SELECT id, username, email, role, created_at FROM users"
    return db.execute_query(query, fetch=True)


def get_admin_statistics() -> dict:
    """Get admin dashboard statistics"""
    query = """
        SELECT
            (SELECT COUNT(*) FROM users WHERE role = 'student') as total_students,
            (SELECT COUNT(*) FROM sessions) as total_sessions,
            (SELECT AVG(focus_score) FROM sessions) as overall_avg_focus_score,
            (SELECT SUM(duration) FROM sessions) as total_study_time_all_users,
            (SELECT COUNT(*) FROM sessions WHERE camera_enabled = TRUE) as sessions_with_camera_enabled,
            (SELECT technique FROM sessions GROUP BY technique ORDER BY COUNT(*) DESC LIMIT 1) as most_popular_technique,
            (SELECT study_mode FROM sessions GROUP BY study_mode ORDER BY COUNT(*) DESC LIMIT 1) as most_popular_mode
    """
    result = db.execute_query(query, fetch=True)
    return result[0] if result else {}


def get_session_statistics() -> list:
    """Get session statistics for all users"""
    query = """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            COUNT(s.id) as total_sessions,
            COALESCE(SUM(s.duration), 0) as total_study_time,
            COALESCE(AVG(s.focus_score), 0) as avg_focus_score,
            COALESCE(SUM(s.distractions), 0) as total_distractions,
            COALESCE(AVG(s.distractions), 0) as avg_distractions_per_session,
            (
                SELECT technique 
                FROM sessions s2 
                WHERE s2.user_id = u.id 
                GROUP BY technique 
                ORDER BY COUNT(*) DESC 
                LIMIT 1
            ) as most_used_technique,
            COUNT(CASE WHEN s.camera_enabled = 1 THEN 1 END) as sessions_with_camera
        FROM users u
        LEFT JOIN sessions s ON u.id = s.user_id
        WHERE u.role = 'student'
        GROUP BY u.id
    """
    return db.execute_query(query, fetch=True)


# Classroom Functions

def create_classroom(name: str, code: str, teacher_id: int) -> int:
    """Create a new classroom"""
    query = "INSERT INTO classrooms (name, code, teacher_id) VALUES (%s, %s, %s)"
    return db.execute_query(query, (name, code, teacher_id))

def get_classroom_by_code(code: str) -> Optional[dict]:
    """Get classroom by unique code"""
    query = "SELECT * FROM classrooms WHERE code = %s"
    result = db.execute_query(query, (code,), fetch=True)
    return result[0] if result else None

def get_classroom_by_id(classroom_id: int) -> Optional[dict]:
    """Get classroom by ID"""
    query = "SELECT * FROM classrooms WHERE id = %s"
    result = db.execute_query(query, (classroom_id,), fetch=True)
    return result[0] if result else None

def is_student_in_classroom(classroom_id: int, student_id: int) -> bool:
    """Check if student is already in classroom"""
    query = "SELECT 1 FROM classroom_students WHERE classroom_id = %s AND student_id = %s"
    result = db.execute_query(query, (classroom_id, student_id), fetch=True)
    return bool(result)

def add_student_to_classroom(classroom_id: int, student_id: int, role: str = 'student'):
    """Add student to classroom"""
    query = "INSERT INTO classroom_students (classroom_id, student_id, role) VALUES (%s, %s, %s)"
    db.execute_query(query, (classroom_id, student_id, role))

def get_teacher_classrooms(teacher_id: int) -> list:
    """Get all classrooms created by a teacher"""
    query = """
        SELECT c.*, COUNT(cs.student_id) as student_count 
        FROM classrooms c 
        LEFT JOIN classroom_students cs ON c.id = cs.classroom_id 
        WHERE c.teacher_id = %s 
        GROUP BY c.id
    """
    return db.execute_query(query, (teacher_id,), fetch=True)

def get_student_classrooms(student_id: int) -> list:
    """Get all classrooms a student has joined"""
    query = """
        SELECT c.*, u.username as teacher_name, cs.role 
        FROM classrooms c
        JOIN classroom_students cs ON c.id = cs.classroom_id
        JOIN users u ON c.teacher_id = u.id
        WHERE cs.student_id = %s
    """
    return db.execute_query(query, (student_id,), fetch=True)

def get_classroom_students_stats(classroom_id: int) -> list:
    """Get statistics for all students in a classroom"""
    # This query aggregates session data ONLY for this classroom
    # If session.classroom_id is NULL, it's not included here.
    query = """
        SELECT 
            u.id as student_id,
            u.username,
            cs.role,
            COUNT(s.id) as total_sessions,
            COALESCE(SUM(s.duration), 0) as total_study_time,
            COALESCE(AVG(s.focus_score), 0) as avg_focus_score
        FROM classroom_students cs
        JOIN users u ON cs.student_id = u.id
        LEFT JOIN sessions s ON u.id = s.user_id AND s.classroom_id = cs.classroom_id
        WHERE cs.classroom_id = %s
        GROUP BY u.id, cs.role
    """
    return db.execute_query(query, (classroom_id,), fetch=True)


def get_student_sessions_for_classroom(classroom_id: int, student_id: int) -> list:
    """Get all sessions for a specific student in a classroom"""
    query = """
        SELECT 
            id, technique, study_mode, duration, focus_score, 
            distractions, timestamp, user_state, camera_enabled
        FROM sessions 
        WHERE user_id = %s AND classroom_id = %s
        ORDER BY timestamp DESC
    """
    return db.execute_query(query, (student_id, classroom_id), fetch=True)


def delete_classroom(classroom_id: int):
    """Delete a classroom and all associated records (cascade)"""
    # Note: Sessions will need classroom_id set to NULL or deleted depending on requirement.
    # Our schema says ON DELETE SET NULL for sessions, and CASCADE for students junction.
    
    query = "DELETE FROM classrooms WHERE id = %s"
    db.execute_query(query, (classroom_id,))


def remove_student_from_classroom(classroom_id: int, student_id: int):
    """Remove a student from a classroom"""
    query = "DELETE FROM classroom_students WHERE classroom_id = %s AND student_id = %s"
    db.execute_query(query, (classroom_id, student_id))


def leave_classroom(classroom_id: int, student_id: int):
    """Student leaves a classroom"""
    query = "DELETE FROM classroom_students WHERE classroom_id = %s AND student_id = %s"
    db.execute_query(query, (classroom_id, student_id))


def update_student_role(classroom_id: int, student_id: int, role: str):
    """Update a student's role in a classroom"""
    query = "UPDATE classroom_students SET role = %s WHERE classroom_id = %s AND student_id = %s"
    db.execute_query(query, (role, classroom_id, student_id))


def get_classroom_representative(classroom_id: int) -> Optional[int]:
    """Get the student ID of the representative for a classroom"""
    query = "SELECT student_id FROM classroom_students WHERE classroom_id = %s AND role = 'representative'"
    result = db.execute_query(query, (classroom_id,), fetch=True)
    return result[0]['student_id'] if result else None



def update_user_system_role(user_id: int, role: str):
    """Update a user's system-wide role (admin only)"""
    query = "UPDATE users SET role = %s WHERE id = %s"
    db.execute_query(query, (role, user_id))


def delete_user(user_id: int):
    """Delete a user account and cascade delete related data"""
    query = "DELETE FROM users WHERE id = %s"
    db.execute_query(query, (user_id,))

def get_all_classrooms() -> list:
    """Get all classrooms system-wide (admin)"""
    query = """
        SELECT c.*, u.username as teacher_name, COUNT(cs.student_id) as student_count 
        FROM classrooms c 
        JOIN users u ON c.teacher_id = u.id
        LEFT JOIN classroom_students cs ON c.id = cs.classroom_id 
        GROUP BY c.id
    """
    return db.execute_query(query, fetch=True)

def get_all_teacher_students(teacher_id: int) -> list:
    """Get all students enrolled in any of the teacher's classrooms"""
    query = """
        SELECT DISTINCT 
            u.id, 
            u.username, 
            u.email,
            GROUP_CONCAT(c.name SEPARATOR ', ') as enrolled_classes
        FROM users u
        JOIN classroom_students cs ON u.id = cs.student_id
        JOIN classrooms c ON cs.classroom_id = c.id
        WHERE c.teacher_id = %s
        GROUP BY u.id
    """
    return db.execute_query(query, (teacher_id,), fetch=True)


def update_user_streak(user_id: int):
    """
    Update study streak for a user.
    Called when a session is successfully completed.
    """
    from datetime import date, timedelta
    
    user = get_user_by_id(user_id)
    if not user: return
    
    today = date.today()
    last_study = user.get('last_study_date')
    current_streak = user.get('streak_count', 0)
    max_streak = user.get('max_streak', 0)
    
    # If already studied today, do nothing
    if last_study == today:
        return
    
    # If studied yesterday, increment streak
    if last_study == today - timedelta(days=1):
        new_streak = current_streak + 1
    else:
        # Streak broken
        new_streak = 1
        
    new_max_streak = max(max_streak, new_streak)
    
    query = """
        UPDATE users 
        SET streak_count = %s, max_streak = %s, last_study_date = %s 
        WHERE id = %s
    """
    db.execute_query(query, (new_streak, new_max_streak, today, user_id))
    logger.info(f"🔥 Streak updated for user {user_id}: {new_streak} days")


def update_user_title_in_db(user_id: int, title: str):
    """Update user title in database"""
    query = "UPDATE users SET title = %s WHERE id = %s"
    db.execute_query(query, (title, user_id))

