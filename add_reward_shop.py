import sqlite3

DATABASE = "cyberescape.db"

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_key TEXT NOT NULL,
    quantity INTEGER DEFAULT 0,
    purchased_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_key),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

conn.commit()
conn.close()

print("Reward shop table created successfully.")