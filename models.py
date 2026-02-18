from flask_login import UserMixin
from bson.objectid import ObjectId
from datetime import datetime

# Collections will be initialized by the application after MongoDB is ready.
COLS = None


def init_collections(cols):
    global COLS
    COLS = cols


class User(UserMixin):
    def __init__(self, user_data):
        # Use manual ID if exists, otherwise fallback to MongoDB _id
        self.id = str(user_data.get('id', user_data.get('_id', '')))
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
        return self.role == 'author'


def _resolve_id(val):
    """Try to resolve an id value to an ObjectId or int/raw value for queries."""
    if val is None:
        return None
    # If looks like ObjectId hex
    try:
        return ObjectId(str(val))
    except Exception:
        try:
            return int(val)
        except Exception:
            return val


class Article:
    @staticmethod
    def create(data):
        data.setdefault('created_at', datetime.utcnow())
        res = COLS['articles'].insert_one(data)
        return str(res.inserted_id)

    @staticmethod
    def get(id):
        _id = _resolve_id(id)
        if isinstance(_id, ObjectId):
            doc = COLS['articles'].find_one({'_id': _id})
        else:
            doc = COLS['articles'].find_one({'id': _id})
        if not doc:
            return None
        if 'id' not in doc or doc.get('id') is None:
            doc['id'] = str(doc.get('_id'))
        return doc

    @staticmethod
    def find(filter=None):
        filter = filter or {}
        docs = list(COLS['articles'].find(filter))
        for d in docs:
            if 'id' not in d or d.get('id') is None:
                d['id'] = str(d.get('_id'))
        return docs

    @staticmethod
    def find_public():
        docs = list(COLS['articles'].find({'is_private': False}))
        for d in docs:
            if 'id' not in d or d.get('id') is None:
                d['id'] = str(d.get('_id'))
        return docs

    @staticmethod
    def find_by_author(author_id):
        docs = list(COLS['articles'].find({'author_id': author_id}))
        for d in docs:
            if 'id' not in d or d.get('id') is None:
                d['id'] = str(d.get('_id'))
        return docs

    @staticmethod
    def update(id, data):
        _id = _resolve_id(id)
        query = {'_id': _id} if isinstance(_id, ObjectId) else {'id': _id}
        COLS['articles'].update_one(query, {'$set': data})

    @staticmethod
    def delete(id):
        _id = _resolve_id(id)
        query = {'_id': _id} if isinstance(_id, ObjectId) else {'id': _id}
        COLS['articles'].delete_one(query)
        # remove related blocks
        COLS['contentblocks'].delete_many({'article_id': id})


class Project:
    @staticmethod
    def create(data):
        data.setdefault('created_at', datetime.utcnow())
        res = COLS['projects'].insert_one(data)
        return str(res.inserted_id)

    @staticmethod
    def get(id):
        _id = _resolve_id(id)
        if isinstance(_id, ObjectId):
            doc = COLS['projects'].find_one({'_id': _id})
        else:
            doc = COLS['projects'].find_one({'id': _id})
        if not doc:
            return None
        if 'id' not in doc or doc.get('id') is None:
            doc['id'] = str(doc.get('_id'))
        return doc

    @staticmethod
    def find(filter=None):
        filter = filter or {}
        docs = list(COLS['projects'].find(filter))
        for d in docs:
            d['id'] = str(d.get('_id'))
        return docs

    @staticmethod
    def find_public():
        docs = list(COLS['projects'].find({'is_private': False}))
        for d in docs:
            d['id'] = str(d.get('_id'))
        return docs

    @staticmethod
    def find_by_author(author_id):
        docs = list(COLS['projects'].find({'author_id': author_id}))
        for d in docs:
            d['id'] = str(d.get('_id'))
        return docs

    @staticmethod
    def update(id, data):
        _id = _resolve_id(id)
        query = {'_id': _id} if isinstance(_id, ObjectId) else {'id': _id}
        COLS['projects'].update_one(query, {'$set': data})

    @staticmethod
    def delete(id):
        _id = _resolve_id(id)
        query = {'_id': _id} if isinstance(_id, ObjectId) else {'id': _id}
        COLS['projects'].delete_one(query)
        COLS['contentblocks'].delete_many({'project_id': id})


class ContentBlock:
    @staticmethod
    def create(data):
        res = COLS['contentblocks'].insert_one(data)
        return str(res.inserted_id)

    @staticmethod
    def find_by_article(article_id):
        # Match numeric IDs, string IDs, and ObjectId hex strings
        query = {'$or': []}
        try:
            query['$or'].append({'article_id': int(article_id)})
        except Exception:
            pass
        query['$or'].append({'article_id': article_id})
        try:
            query['$or'].append({'article_id': ObjectId(str(article_id))})
        except Exception:
            pass
        return list(COLS['contentblocks'].find(query).sort('sequence', 1))

    @staticmethod
    def find_by_project(project_id):
        query = {'$or': []}
        try:
            query['$or'].append({'project_id': int(project_id)})
        except Exception:
            pass
        query['$or'].append({'project_id': project_id})
        try:
            query['$or'].append({'project_id': ObjectId(str(project_id))})
        except Exception:
            pass
        return list(COLS['contentblocks'].find(query).sort('sequence', 1))

    @staticmethod
    def delete_by_article(article_id):
        COLS['contentblocks'].delete_many({'article_id': article_id})

    @staticmethod
    def delete_by_project(project_id):
        COLS['contentblocks'].delete_many({'project_id': project_id})


class Reminder:
    @staticmethod
    def find_all():
        return list(COLS['reminders'].find())


class Member:
    @staticmethod
    def find_all():
        return list(COLS['members'].find())

