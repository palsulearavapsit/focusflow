
import mysql.connector
from config import settings

def check_schema():
    try:
        conn = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("DESCRIBE sessions")
        columns = cursor.fetchall()
        for col in columns:
            if col[0] == 'study_mode':
                print(f"study_mode type: {col[1]}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
