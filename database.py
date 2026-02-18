import os
from pymongo import MongoClient


def init_mongodb():
    """Initialize MongoDB client and return client and primary database object.

    Collections are not imported here to avoid circular imports; call
    `get_collections()` after initialization to retrieve collection handles.
    """
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db_mongo = client.get_database('hackerspace_auth')

    return client, db_mongo


def get_collections(db_mongo):
    """Return a dict of commonly used collection handles."""
    return {
        'users': db_mongo['users'],
        'articles': db_mongo['articles'],
        'projects': db_mongo['projects'],
        'contentblocks': db_mongo['contentblocks'],
        'reminders': db_mongo['reminders'],
        'members': db_mongo['members']
    }


def seed_database(db_mongo):
    """Seed some sample documents into MongoDB if collections are empty."""
    cols = get_collections(db_mongo)

    # Seed projects
    if cols['projects'].count_documents({}) == 0:
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
        cols['articles'].insert_many([
            {'title': 'Opening!', 'author': 'WUSL Team', 'is_private': False},
            {'title': 'Top Tools', 'author': 'WUSL Team', 'is_private': False}
        ])

    # Seed reminders
    if cols['reminders'].count_documents({}) == 0:
        cols['reminders'].insert_many([
            {'text': 'Sync repos.'},
            {'text': 'Update board.'},
            {'text': 'Espresso!'},
            {'text': 'PR Review.'},
            {'text': 'Stand-up.'}
        ])

    # Seed members
    if cols['members'].count_documents({}) == 0:
        cols['members'].insert_many([
            {'name': 'Aris Thorne', 'role': 'Lead', 'avatar': 'https://i.pravatar.cc/150?u=aris'},
            {'name': 'Sarah Jenkins', 'role': 'Hardware', 'avatar': 'https://i.pravatar.cc/150?u=sarah'}
        ])
