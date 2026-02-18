from flask import Blueprint, jsonify
import os
from database import init_mongodb

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug-db')
def debug_db():
    uri = os.getenv("MONGO_URI")
    if not uri:
        return jsonify({"status": "error", "message": "MONGO_URI not set in environment variables"}), 500
    
    # Mask usage of URI for security
    masked_uri = uri.replace(uri.split('@')[0], 'Reserved') if '@' in uri else 'Invalid format'

    try:
        client, db = init_mongodb()
        # Force a command to test connection
        client.admin.command('ping')
        return jsonify({
            "status": "success", 
            "message": "Connected to MongoDB!", 
            "masked_uri": masked_uri,
            "db_name": db.name
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e), 
            "masked_uri": masked_uri
        }), 500
