"""
FocusFlow Supabase Database Module
Replaces MySQL connection with Supabase client
"""

from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    """Supabase Client wrapper for FocusFlow"""
    
    def __init__(self):
        """Initialize Supabase client"""
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.warning("⚠️ Supabase URL or Key missing in config")
            self.client = None
            return
            
        try:
            self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("✅ Supabase connection initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
            self.client = None

    def test_connection(self) -> bool:
        """Test database connection (via fetching first user)"""
        if not self.client: return False
        try:
            # Simple test query to 'profiles' table
            self.client.table("profiles").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Supabase test failed: {e}")
            return False

# Global database instance
db = Database()

# Helper Functions using Supabase API

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get profile by UUID"""
    response = db.client.table("profiles").select("*").eq("id", user_id).single().execute()
    return response.data if response.data else None

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get profile by email"""
    response = db.client.table("profiles").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None

def create_session(session_data: Dict) -> Dict:
    """Create a new study session"""
    response = db.client.table("sessions").insert(session_data).execute()
    return response.data[0] if response.data else {}

def get_user_sessions(user_id: str, limit: int = 10) -> List[Dict]:
    """Get user's session history"""
    response = db.client.table("sessions").select("*").eq("user_id", user_id).order("timestamp", desc=True).limit(limit).execute()
    return response.data if response.data else []

def get_admin_statistics() -> Dict:
    """Get stats using RPC (Stored Procedure) or direct count"""
    # Simple direct counts for now
    students = db.client.table("profiles").select("id", count="exact").eq("role", "student").execute()
    sessions = db.client.table("sessions").select("id", count="exact").execute()
    return {
        "total_students": students.count,
        "total_sessions": sessions.count
    }

def create_classroom(name: str, code: str, teacher_id: str) -> Dict:
    """Create a new classroom"""
    data = {"name": name, "code": code, "teacher_id": teacher_id}
    response = db.client.table("classrooms").insert(data).execute()
    return response.data[0] if response.data else {}

def get_classroom_by_code(code: str) -> Optional[Dict]:
    """Get classroom by code"""
    response = db.client.table("classrooms").select("*").eq("code", code).execute()
    return response.data[0] if response.data else None

def add_student_to_classroom(classroom_id: str, student_id: str):
    """Enroll student in classroom"""
    data = {"classroom_id": classroom_id, "student_id": student_id}
    db.client.table("classroom_students").insert(data).execute()

def get_teacher_classrooms(teacher_id: str) -> List[Dict]:
    """Get classrooms created by teacher"""
    response = db.client.table("classrooms").select("*, classroom_students(count)").eq("teacher_id", teacher_id).execute()
    return response.data if response.data else []

def update_user_streak(user_id: str):
    """
    Supabase Trigger usually handles this, but here's the API-way
    Supabase's 'profiles' table will store this.
    """
    from datetime import date
    today = date.today().isoformat()
    db.client.table("profiles").update({"last_study_date": today}).eq("id", user_id).execute()
    # Note: Complex streak logic is better in SQL Function in Supabase
