import sqlite3
import sqlalchemy
from app.database import engine

print(engine.name)
if engine.name == "sqlite":
    conn = sqlite3.connect("./investment_advisory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE clients ADD COLUMN extracted_info JSON;")
        conn.commit()
        print("Successfully added extracted_info column to SQLite clients table.")
    except Exception as e:
        print("Warning/Error:", e)
    conn.close()
elif engine.name == "postgresql":
    conn = engine.connect()
    try:
        conn.execute(sqlalchemy.text("ALTER TABLE clients ADD COLUMN extracted_info JSONB;"))
        conn.commit()
        print("Successfully added extracted_info column to PostgreSQL clients table.")
    except Exception as e:
        print("Warning/Error:", e)
    conn.close()
