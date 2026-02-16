import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import db

def demote_student():
    classroom_id = 20
    student_id = 15
    student_username = 's2'
    
    print(f"Demoting student '{student_username}' (ID: {student_id}) in classroom {classroom_id}...")
    
    try:
        # Check current role first
        query = "SELECT role FROM classroom_students WHERE classroom_id = %s AND student_id = %s"
        result = db.execute_query(query, (classroom_id, student_id), fetch=True)
        
        if result:
            current_role = result[0]['role']
            print(f"Current role: {current_role}")
            
            if current_role == 'representative':
                # Update role
                query = "UPDATE classroom_students SET role = 'student' WHERE classroom_id = %s AND student_id = %s"
                db.execute_query(query, (classroom_id, student_id))
                print(f"Successfully updated role to 'student'!")
            else:
                print("Role is not representative, skipping update.")
        else:
            print("Student not found in classroom.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if db.test_connection():
        demote_student()
    else:
        print("Failed to connect to DB.")
