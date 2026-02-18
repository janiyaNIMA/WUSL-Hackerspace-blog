import os
from pymongo import MongoClient
from extensions import db
from models import Project, Article, Reminder, Member

def init_mongodb():
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db_mongo = client['hackerspace_auth']
    users_col = db_mongo['users']
    
    # Connection test
    try:
        client.admin.command('ping')
        print("✅ MongoDB Connection Successful!")
    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")
        
    return client, users_col

def seed_database(app):
    with app.app_context():
        db.create_all()
        
        if Project.query.count() == 0:
            db.session.add_all([
                Project(title="Quantum Hack Tracker", description="Real-time monitoring system.", thumbnail="https://img.freepik.com/free-vector/cyber-security-concept_23-2148534431.jpg", color="#a29bfe"),
                Project(title="Neural Mesh Network", description="Decentralized protocol.", thumbnail="https://img.freepik.com/free-vector/abstract-digital-technology-background-with-mesh-lines_1017-26300.jpg", color="#fab1a0")
            ])
        if Article.query.count() == 0:
            db.session.add_all([Article(title="Opening!", content="Lab space opened."), Article(title="Top Tools", content="Curated list.")])
        if Reminder.query.count() == 0:
            db.session.add_all([Reminder(text="Sync repos."), Reminder(text="Update board."), Reminder(text="Espresso!"), Reminder(text="PR Review."), Reminder(text="Stand-up.")])
        if Member.query.count() == 0:
            db.session.add_all([Member(name="Aris Thorne", role="Lead", avatar="https://i.pravatar.cc/150?u=aris"), Member(name="Sarah Jenkins", role="Hardware", avatar="https://i.pravatar.cc/150?u=sarah")])
        
        db.session.commit()
