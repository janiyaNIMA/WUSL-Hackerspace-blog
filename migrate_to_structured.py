import sqlite3
import json
import os

db_path = 'hackerspace.db'
if not os.path.exists(db_path):
    print("Database not found.")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Create content_block table
cursor.execute('''
CREATE TABLE IF NOT EXISTS content_block (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER,
    project_id INTEGER,
    type VARCHAR(50),
    sub_type VARCHAR(50),
    value TEXT,
    sequence INTEGER,
    FOREIGN KEY(article_id) REFERENCES article(id),
    FOREIGN KEY(project_id) REFERENCES project(id)
)
''')

# 2. Migrate existing Article data
cursor.execute("SELECT id, content FROM article")
articles = cursor.fetchall()
for art_id, content in articles:
    try:
        blocks = json.loads(content)
        for i, block in enumerate(blocks):
            cursor.execute('''
                INSERT INTO content_block (article_id, type, sub_type, value, sequence)
                VALUES (?, ?, ?, ?, ?)
            ''', (art_id, block['type'], block['sub_type'], block.get('value', ''), i))
    except (json.JSONDecodeError, TypeError):
        # Fallback if it was just plain text
        cursor.execute('''
            INSERT INTO content_block (article_id, type, sub_type, value, sequence)
            VALUES (?, ?, ?, ?, ?)
        ''', (art_id, 'text', 'paragraph', content, 0))

# 3. Migrate existing Project data
cursor.execute("SELECT id, description FROM project")
projects = cursor.fetchall()
for proj_id, desc in projects:
    try:
        blocks = json.loads(desc)
        for i, block in enumerate(blocks):
            cursor.execute('''
                INSERT INTO content_block (project_id, type, sub_type, value, sequence)
                VALUES (?, ?, ?, ?, ?)
            ''', (proj_id, block['type'], block['sub_type'], block.get('value', ''), i))
    except (json.JSONDecodeError, TypeError):
        # Fallback
        cursor.execute('''
            INSERT INTO content_block (project_id, type, sub_type, value, sequence)
            VALUES (?, ?, ?, ?, ?)
        ''', (proj_id, 'text', 'paragraph', desc, 0))

# 4. We can't easily drop columns in SQLite without recreating the table.
# For now, we leave the old columns, but the app will use the new table.

conn.commit()
conn.close()
print("Migration to structured blocks complete!")
