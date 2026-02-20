
import mysql.connector
from config import settings

def update_schema():
    try:
        conn = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        cursor = conn.cursor()
        print("Modifying sessions table...")
        cursor.execute("ALTER TABLE sessions MODIFY COLUMN study_mode ENUM('screen', 'book', 'group') NOT NULL")
        conn.commit()
        print("Schema updated successfully!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_schema()
