from extensions import db
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data):
        # Use manual ID if exists, otherwise fallback to MongoDB _id
        self.id = str(user_data.get('id', user_data['_id']))
        self.username = user_data.get('username', 'Unknown')
        self.email = user_data.get('email', '')
        self.avatar = user_data.get('avatar', '')
        self.role = user_data.get('role', 'user')
        if self.email == 'admin@wusl.com':
            self.role = 'super_admin'

    @property
    def is_admin(self):
        return self.role == 'super_admin'

    @property
    def is_author(self):
        return self.role =='author'

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), default="WUSL Team")
    author_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    is_private = db.Column(db.Boolean, default=False)
    
    # Relationship to structured blocks
    blocks = db.relationship('ContentBlock', backref='article', lazy=True, cascade="all, delete-orphan", order_by="ContentBlock.sequence")

    def to_dict(self):
        return {
            "id": self.id, 
            "title": self.title, 
            "author": self.author, 
            "date": self.created_at.strftime("%Y-%m-%d"),
            "is_private": self.is_private,
            "blocks": [b.to_dict() for b in self.blocks]
        }

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    thumbnail = db.Column(db.String(200))
    color = db.Column(db.String(20))
    author_id = db.Column(db.String(100))
    is_private = db.Column(db.Boolean, default=False)
    
    # Relationship to structured blocks
    blocks = db.relationship('ContentBlock', backref='project', lazy=True, cascade="all, delete-orphan", order_by="ContentBlock.sequence")
    
    def to_dict(self):
        return {
            "id": self.id, 
            "title": self.title, 
            "thumbnail": self.thumbnail, 
            "color": self.color,
            "is_private": self.is_private,
            "blocks": [b.to_dict() for b in self.blocks]
        }

class ContentBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    
    type = db.Column(db.String(50)) # 'text' or 'media'
    sub_type = db.Column(db.String(50)) # 'paragraph', 'heading', 'image', 'video'
    value = db.Column(db.Text) # The actual content or URL
    sequence = db.Column(db.Integer) # Keeps the order of blocks
    
    def to_dict(self):
        return {
            "type": self.type,
            "sub_type": self.sub_type,
            "value": self.value
        }

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    def to_dict(self):
        return {"id": self.id, "text": self.text}

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    avatar = db.Column(db.String(200))
    def to_dict(self):
        return {"id": self.id, "name": self.name, "role": self.role, "avatar": self.avatar}
