import sqlite3
import os

db_path = 'hackerspace.db'
if not os.path.exists(db_path):
    print(f"{db_path} not found. Server should create it on start.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def add_column(table, column, type, default=None):
        try:
            sql = f"ALTER TABLE {table} ADD COLUMN {column} {type}"
            if default is not None:
                sql += f" DEFAULT {default}"
            cursor.execute(sql)
            print(f"✅ Added {table}.{column}")
        except sqlite3.OperationalError:
            print(f"ℹ️ {table}.{column} already exists")

    add_column('project', 'author_id', 'VARCHAR(100)')
    add_column('project', 'is_private', 'BOOLEAN', default='0')
    add_column('article', 'author_id', 'VARCHAR(100)')
    add_column('article', 'is_private', 'BOOLEAN', default='0')

    conn.commit()
    conn.close()
    print("Migration complete.")
