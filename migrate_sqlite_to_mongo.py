"""
Migrate data from `hackerspace.db` (SQLite) into MongoDB collections used by the app.

Usage:
    python migrate_sqlite_to_mongo.py

It will:
 - Read all rows from common tables (users, article, project, content_block, reminders, member)
 - Insert documents into MongoDB collections with the same column names
 - Preserve numeric `id` values by saving them as `id` field on the document so
   the application can still resolve legacy integer IDs.

Note: ensure `MONGO_URI` env var is set if not running Mongo locally.
"""

import sqlite3
import os
import json
from database import init_mongodb, get_collections

SQLITE_DB = 'hackerspace.db'

if not os.path.exists(SQLITE_DB):
    print(f"SQLite DB '{SQLITE_DB}' not found. Nothing to migrate.")
    exit(0)

# Initialize MongoDB
client, db_mongo = init_mongodb()
cols = get_collections(db_mongo)

# Connect SQLite
conn = sqlite3.connect(SQLITE_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Helper to migrate a table to a collection
def migrate_table(table_name, collection_name, transform_row=None):
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cur.fetchone():
        print(f"Table '{table_name}' not found in SQLite, skipping.")
        return 0

    cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()
    if not rows:
        print(f"No rows found in {table_name}.")
        return 0

    docs = []
    for r in rows:
        doc = dict(r)
        # Preserve existing integer id as `id` field if present
        if 'id' in doc and doc['id'] is not None:
            try:
                doc['id'] = int(doc['id'])
            except Exception:
                pass
        # Transform row if a custom function provided
        if transform_row:
            doc = transform_row(doc)
        docs.append(doc)

    if docs:
        # Insert many, but avoid duplicate insertion if collection already populated
        existing = cols[collection_name].count_documents({})
        if existing == 0:
            cols[collection_name].insert_many(docs)
            print(f"Inserted {len(docs)} documents into '{collection_name}'.")
        else:
            print(f"Collection '{collection_name}' already has data ({existing} docs); skipping insert.")
    return len(docs)

# Migrate users
migrate_table('users', 'users')

# Migrate articles
# If the app used a column `content` storing structured blocks as JSON, leave as-is
migrate_table('article', 'articles')

# Migrate projects
migrate_table('project', 'projects')

# Migrate content_block -> contentblocks
migrate_table('content_block', 'contentblocks')

# Migrate reminders
migrate_table('reminder', 'reminders')

# Migrate members
migrate_table('member', 'members')

conn.close()
print('SQLite -> MongoDB migration finished.')
