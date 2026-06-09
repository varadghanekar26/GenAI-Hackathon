import sqlite3

DB_NAME = "meetings.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meetings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        summary TEXT,
        raw_text TEXT,
        analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("PRAGMA table_info(meetings)")
    meeting_columns = {row[1] for row in cursor.fetchall()}
    if "analyzed_at" not in meeting_columns:
        cursor.execute("ALTER TABLE meetings ADD COLUMN analyzed_at TEXT")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER,
        name TEXT,
        status TEXT,
        FOREIGN KEY(meeting_id) REFERENCES meetings(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS action_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER,
        task TEXT,
        owner TEXT,
        deadline TEXT,
        status TEXT DEFAULT 'open',
        FOREIGN KEY(meeting_id) REFERENCES meetings(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS risks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER,
        description TEXT,
        severity TEXT,
        FOREIGN KEY(meeting_id) REFERENCES meetings(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS escalations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER,
        issue TEXT,
        raised_by TEXT,
        status TEXT DEFAULT 'open',
        FOREIGN KEY(meeting_id) REFERENCES meetings(id)
    )
    """)

    cursor.execute("PRAGMA table_info(escalations)")
    escalation_columns = {row[1] for row in cursor.fetchall()}
    if "status" not in escalation_columns:
        cursor.execute("ALTER TABLE escalations ADD COLUMN status TEXT DEFAULT 'open'")

    conn.commit()
    conn.close()
