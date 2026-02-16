import sys
import os

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db

def check_structure():
    try:
        if db.test_connection():
            print("Connected to database.")
            
            # Get classrooms
            classrooms = db.execute_query("SELECT id, name, code FROM classrooms", fetch=True)
            print(f"\nClassrooms found: {len(classrooms)}")
            for c in classrooms:
                print(f"ID: {c['id']}, Name: '{c['name']}', Code: '{c['code']}'")
                
                # Get students in this classroom
                students = db.execute_query("""
                    SELECT u.id, u.username, cs.role 
                    FROM classroom_students cs
                    JOIN users u ON cs.student_id = u.id
                    WHERE cs.classroom_id = %s
                """, (c['id'],), fetch=True)
                
                if students:
                    print(f"  Students ({len(students)}):")
                    for s in students:
                        print(f"    - ID: {s['id']}, Username: '{s['username']}', Role: '{s['role']}'")
                else:
                    print("  No students in this classroom.")
                    
        else:
            print("Failed to connect.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_structure()
