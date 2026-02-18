import os
import certifi
from pymongo import MongoClient

# Singleton client storage
_mongo_client = None
_db_instance = None

def get_mongo_connection():
    """
    Establish or retrieve the MongoDB client and database connection.
    This function implements a singleton pattern to reuse the database connection
    across potential multiple calls within the same worker context, although
    Vercel runtime environment is stateless, this helps in local and persistent contexts.
    
    Returns:
        tuple: (client, db)
    """
    global _mongo_client, _db_instance

    # If connection already exists and check if client is still alive (optional)
    if _mongo_client is not None and _db_instance is not None:
        return _mongo_client, _db_instance

    # Fetch URI from environment with a fallback (Note: Fallback contains credentials)
    # WARNING: Hardcoded credentials should ideally be avoided in production code.
    uri = os.getenv("MONGO_URI", "mongodb+srv://janidunimsarabro_db_user:0625@cluster0.o1tm36u.mongodb.net/")
    
    if not uri:
        # If no URI is provided, we cannot proceed.
        # Raising an exception here will be caught by the calling function in app.py
        raise ValueError("CRITICAL: MONGO_URI environment variable is not set and no fallback available.")

    try:
        # Initialize MongoClient with recommended timeouts for serverless
        # connectTimeoutMS: Time to wait for initial connection
        # serverSelectionTimeoutMS: Time to wait to find a server
        # tlsCAFile: Explicitly use certifi CA bundle to fix SSL errors
        print(f"INFO: Connecting to MongoDB...")
        _mongo_client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            tlsCAFile=certifi.where()
        )
        
        # Select the database
        _db_instance = _mongo_client.get_database('hackerspace_auth')
        
        # Verify connection (lazy check, but we want to fail fast if config is wrong)
        # Note: In strictly serverless, you might skip 'ping' to save ms, 
        # but for debugging stability issues, a quick check is valuable.
        # We can disable this in high-traffic production if needed.
        # _mongo_client.admin.command('ping')
        print("SUCCESS: Connected to MongoDB.")
        
        return _mongo_client, _db_instance

    except Exception as e:
        print(f"ERROR: Failed to initialize MongoDB client: {e}")
        # Reset globals on failure to ensure retry on next call
        _mongo_client = None
        _db_instance = None
        raise e

def init_mongodb():
    """Wrapper function to maintain backward compatibility with app.py calls"""
    return get_mongo_connection()

def get_collections(db):
    """
    Return a dictionary of collection handles for easy access.
    
    Args:
        db: The MongoDB database object
        
    Returns:
        dict: Keys are collection names, values are PyMongo collection objects
    """
    if db is None:
        return {}
        
    return {
        'users': db['users'],
        'articles': db['articles'],
        'projects': db['projects'],
        'contentblocks': db['contentblocks'],
        'reminders': db['reminders'],
        'members': db['members']
    }

def seed_database(db):
    """
    Seed initial data if collections are empty.
    Useful for fresh deployments.
    """
    if db is None:
        return

    cols = get_collections(db)
    
    try:
        # Seed projects
        if cols['projects'].count_documents({}) == 0:
            print("INFO: Seeding projects...")
            cols['projects'].insert_many([
                {
                    'title': 'Quantum Hack Tracker',
                    'description': 'Real-time monitoring system.',
                    'thumbnail': 'https://img.freepik.com/free-vector/cyber-security-concept_23-2148534431.jpg',
                    'color': '#a29bfe',
                    'is_private': False
                },
                {
                    'title': 'Neural Mesh Network',
                    'description': 'Decentralized protocol.',
                    'thumbnail': 'https://img.freepik.com/free-vector/abstract-digital-technology-background-with-mesh-lines_1017-26300.jpg',
                    'color': '#fab1a0',
                    'is_private': False
                }
            ])

        # Seed articles
        if cols['articles'].count_documents({}) == 0:
            print("INFO: Seeding articles...")
            cols['articles'].insert_many([
                {'title': 'Opening!', 'author': 'WUSL Team', 'is_private': False},
                {'title': 'Top Tools', 'author': 'WUSL Team', 'is_private': False}
            ])

        # Seed reminders
        if cols['reminders'].count_documents({}) == 0:
            print("INFO: Seeding reminders...")
            cols['reminders'].insert_many([
                {'text': 'Sync repos.'},
                {'text': 'Update board.'},
                {'text': 'Espresso!'},
                {'text': 'PR Review.'},
                {'text': 'Stand-up.'}
            ])

        # Seed members
        if cols['members'].count_documents({}) == 0:
            print("INFO: Seeding members...")
            cols['members'].insert_many([
                {'name': 'Aris Thorne', 'role': 'Lead', 'avatar': 'https://i.pravatar.cc/150?u=aris'},
                {'name': 'Sarah Jenkins', 'role': 'Hardware', 'avatar': 'https://i.pravatar.cc/150?u=sarah'}
            ])
            
    except Exception as e:
        print(f"WARNING: Database seeding failed: {e}")
