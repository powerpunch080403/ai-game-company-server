import sqlite3
from datetime import datetime, UTC

def main():
    conn = sqlite3.connect('./data/game_company.sqlite3')
    now = datetime.now(UTC).isoformat()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = 'merged', completed_at = ? WHERE id = 1", (now,))
    cursor.execute(
        "INSERT INTO task_events (task_id, event_type, message, created_at) VALUES (?, ?, ?, ?)",
        (1, 'merged', 'Merged manually to main.', now)
    )
    conn.commit()
    conn.close()
    print("Task 1 marked as merged in database successfully!")

if __name__ == "__main__":
    main()
