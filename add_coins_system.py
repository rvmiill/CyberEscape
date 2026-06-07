import sqlite3

DATABASE = "cyberescape.db"

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0")
    print("coins column added to users table.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("coins column already exists.")
    else:
        print("Error adding coins column:", e)

try:
    cursor.execute("ALTER TABLE game_progress ADD COLUMN coins_awarded INTEGER DEFAULT 0")
    print("coins_awarded column added to game_progress table.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("coins_awarded column already exists.")
    else:
        print("Error adding coins_awarded column:", e)

conn.commit()
conn.close()

print("Cyber Coins database update completed.")