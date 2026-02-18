from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId
import os
import json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Import separated modules
from extensions import bcrypt, login_manager
from database import init_mongodb, get_collections, seed_database

# Load .env file (only for local development)
load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-key-if-missing')

    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Register Debug Route
    from debug_routes import debug_bp
    app.register_blueprint(debug_bp)
    
    return app

app = create_app()

# Initialize MongoDB lazily
def get_db():
    if not hasattr(app, 'db_cols') or app.db_cols is None:
        try:
            mongo_client, db_mongo = init_mongodb()
            app.db_cols = get_collections(db_mongo)
            from models import init_collections
            init_collections(app.db_cols)
        except Exception as e:
            print(f"CRITICAL: Failed to connect to MongoDB: {e}")
            import traceback
            traceback.print_exc()
            app.db_cols = None
    return app.db_cols

@app.before_request
def ensure_db_connection():
    get_db()

# Helper to get users collection safely
def get_users_col():
    cols = get_db()
    return cols['users'] if cols else None

def get_user_query(uid):
    if str(uid).isdigit():
        # Check both manual 'id' field and primary '_id' field for numeric strings
        return {"$or": [{"id": int(uid)}, {"_id": str(uid)}, {"_id": int(uid)}]}
    try:
        return {"_id": ObjectId(uid)}
    except:
        return {"_id": uid}

@login_manager.user_loader
def load_user(user_id):
    try:
        query = get_user_query(user_id)
        users_col = get_users_col()
        if users_col is not None:
            user_data = users_col.find_one(query)
            if user_data:
                # print(f"--- [AUTH DEBUG] Loaded: {user_data.get('username')} ---")
                return User(user_data)
    except Exception as e:
        print(f"--- [AUTH ERROR] Failed to load user: {e} ---")
    return None

# --- Auth Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            users_col = get_users_col()
            if users_col is None:
                flash("Database not ready. check MONGO_URI.")
                return redirect(url_for('signup'))

            if users_col.find_one({"email": email}):
                flash('Email already exists')
                return redirect(url_for('signup'))
            
            role = 'user'
            if users_col.count_documents({}) == 0 or email == 'admin@wusl.com':
                role = 'super_admin'

            # Get next manual ID
            max_user = users_col.find_one(sort=[("id", -1)])
            next_id = (max_user.get('id', 0) + 1) if max_user and 'id' in max_user else 1

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            users_col.insert_one({
                "id": next_id,
                "username": username,
                "email": email,
                "password": hashed_password,
                "role": role
            })
            flash('Signup successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Database error during signup: {e}')
            return redirect(url_for('signup'))
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            users_col = get_users_col()
            if users_col is None:
                flash("Database connection failed. Please check server logs.")
                return redirect(url_for('login'))

            user_data = users_col.find_one({"email": email})
            
            if not user_data:
                print(f"❌ Login failed: User {email} not found.")
                flash('Invalid email or password')
            elif bcrypt.check_password_hash(user_data['password'], password):
                user_obj = User(user_data)
                login_user(user_obj)
                print(f"✅ User {email} logged in successfully.")
                return redirect(url_for('index'))
            else:
                print(f"❌ Login failed: Password mismatch for {email}.")
                flash('Invalid email or password')
        except Exception as e:
            print(f"❌ DATABASE ERROR during login: {e}")
            flash('Database connection error. Please try again later.')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        avatar = request.form.get('avatar')
        password = request.form.get('password')

        update_data = {
            "username": username,
            "email": email,
            "avatar": avatar
        }

        if password:
            update_data["password"] = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            users_col = get_users_col()
            users_col.update_one(
                get_user_query(current_user.id),
                {"$set": update_data}
            )
            flash('Profile updated successfully!')
            return redirect(url_for('edit_profile'))
        except Exception as e:
            flash(f'Error updating profile: {e}')
            
    return render_template('edit_profile.html')

# --- Main Routes ---
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('guest.html')
    return render_template('index.html')

@app.route('/news')
@login_required
def news():
    return render_template('news.html')

@app.route('/create-article', methods=['GET', 'POST'])
@login_required
def create_article():
    if not current_user.is_author:
        flash('Permission denied. Only authors can access this page.')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        content_type = request.form.get('content_type')
        blocks_data_str = request.form.get('blocks_data')
        
        try:
            blocks = json.loads(blocks_data_str)

            # Handle file uploads for each block
            for block in blocks:
                if block.get('file_key') and block['file_key'] in request.files:
                    file = request.files[block['file_key']]
                    if file and file.filename:
                        original_filename = secure_filename(file.filename)
                        # Add a unique prefix to prevent overwriting
                        filename = f"{ObjectId()}_{original_filename}"
                        save_path = os.path.join('static', 'uploads', 'content', filename)
                        file.save(os.path.join(app.root_path, save_path))
                        block['value'] = '/' + save_path.replace('\\', '/')

            if content_type == 'news':
                new_id = Article.create({
                    'title': title,
                    'author': current_user.username,
                    'author_id': current_user.id,
                    'is_private': False
                })
            else:
                new_id = Project.create({
                    'title': title,
                    'color': '#fdfaf6',
                    'author_id': current_user.id,
                    'is_private': False
                })

            # Create structured blocks
            for i, block_data in enumerate(blocks):
                block_doc = {
                    'article_id': new_id if content_type == 'news' else None,
                    'project_id': new_id if content_type == 'project' else None,
                    'type': block_data['type'],
                    'sub_type': block_data['sub_type'],
                    'value': block_data.get('value', ''),
                    'sequence': i
                }
                ContentBlock.create(block_doc)

            target_page = 'news' if content_type == 'news' else 'index'
            flash(f'{"Article" if content_type == "news" else "Project"} published successfully!')
            return redirect(url_for(target_page))

        except Exception as e:
            print(f"Error publishing: {e}")
            flash(f'Error publishing content: {e}')
            
    return render_template('create_article.html')

@app.route('/members')
@login_required
def members():
    return render_template('members.html')

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/manage-content')
@login_required
def manage_content():
    if not current_user.is_author and not current_user.is_admin:
        flash('Permission denied.')
        return redirect(url_for('index'))
    
    # Authors see their own, Admins see everything
    if current_user.is_admin:
        articles = Article.find()
        projects = Project.find()
    else:
        articles = Article.find_by_author(current_user.id)
        projects = Project.find_by_author(current_user.id)
        
    return render_template('manage_content.html', articles=articles, projects=projects)

@app.route('/edit-content/<type>/<id>', methods=['GET', 'POST'])
@login_required
def edit_content(type, id):
    item = Article.get(id) if type == 'news' else Project.get(id)
    if not item:
        flash('Item not found.')
        return redirect(url_for('manage_content'))

    author_id = item.get('author_id') if isinstance(item, dict) else getattr(item, 'author_id', None)
    if author_id != current_user.id and not current_user.is_admin:
        flash('Permission denied.')
        return redirect(url_for('manage_content'))

    if request.method == 'POST':
        title = request.form.get('title')
        blocks_data_str = request.form.get('blocks_data')

        try:
            blocks = json.loads(blocks_data_str)
            # Handle new file uploads
            for block in blocks:
                if block.get('file_key') and block['file_key'] in request.files:
                    file = request.files[block['file_key']]
                    if file and file.filename:
                        filename = f"{ObjectId()}_{secure_filename(file.filename)}"
                        save_path = os.path.join('static', 'uploads', 'content', filename)
                        file.save(os.path.join(app.root_path, save_path))
                        block['value'] = '/' + save_path.replace('\\', '/')

            # Update title
            if type == 'news':
                Article.update(id, {'title': title})
            else:
                Project.update(id, {'title': title})

            # Clear existing blocks and recreate
            if type == 'news':
                ContentBlock.delete_by_article(id)
            else:
                ContentBlock.delete_by_project(id)

            for i, block_data in enumerate(blocks):
                block_doc = {
                    'article_id': id if type == 'news' else None,
                    'project_id': id if type != 'news' else None,
                    'type': block_data['type'],
                    'sub_type': block_data['sub_type'],
                    'value': block_data.get('value', ''),
                    'sequence': i
                }
                ContentBlock.create(block_doc)

            flash('Content updated successfully!')
            return redirect(url_for('manage_content'))

        except Exception as e:
            flash(f'Error updating content: {e}')

    # Pass existing blocks as JSON list for the frontend editor
    if type == 'news':
        blocks = ContentBlock.find_by_article(id)
    else:
        blocks = ContentBlock.find_by_project(id)
    blocks_list = [{'type': b.get('type'), 'sub_type': b.get('sub_type'), 'value': b.get('value')} for b in blocks]
    return render_template('create_article.html', 
                          item=item, 
                          content_type=type, 
                          existing_blocks=json.dumps(blocks_list))

@app.route('/toggle-visibility/<type>/<id>')
@login_required
def toggle_visibility(type, id):
    item = Article.get(id) if type == 'news' else Project.get(id)
    if not item:
        flash('Item not found.')
        return redirect(url_for('manage_content'))

    author_id = item.get('author_id') if isinstance(item, dict) else getattr(item, 'author_id', None)
    if author_id != current_user.id and not current_user.is_admin:
        flash('Permission denied.')
        return redirect(url_for('manage_content'))

    current = item.get('is_private', False) if isinstance(item, dict) else getattr(item, 'is_private', False)
    if type == 'news':
        Article.update(id, {'is_private': not current})
    else:
        Project.update(id, {'is_private': not current})

    flash('Visibility updated.')
    return redirect(url_for('manage_content'))

@app.route('/delete-content/<type>/<id>')
@login_required
def delete_content(type, id):
    item = Article.get(id) if type == 'news' else Project.get(id)
    if not item:
        flash('Item not found.')
        return redirect(url_for('manage_content'))

    author_id = item.get('author_id') if isinstance(item, dict) else getattr(item, 'author_id', None)
    if author_id != current_user.id and not current_user.is_admin:
        flash('Permission denied.')
        return redirect(url_for('manage_content'))

    if type == 'news':
        Article.delete(id)
    else:
        Project.delete(id)

    flash('Item deleted successfully.')
    return redirect(url_for('manage_content'))

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('Access denied. Admin only.')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('role')
        
        try:
            users_col = get_users_col()
            users_col.update_one(
                get_user_query(user_id),
                {"$set": {"role": new_role}}
            )
            flash('User role updated successfully!')
        except Exception as e:
            flash(f'Error updating role: {e}')
        return redirect(url_for('manage_users'))

    # Fetch all users
    try:
        users_col = get_users_col()
        users = list(users_col.find())
        return render_template('manage_users.html', users=users)
    except Exception as e:
        flash(f'Error fetching users: {e}')
        return redirect(url_for('index'))

# --- API Routes ---
@app.route('/api/projects')
def get_projects():
    # Only return public projects
    projects = Project.find_public()
    return jsonify(projects)

@app.route('/api/articles')
def get_articles():
    # Only return public articles
    articles = Article.find_public()
    return jsonify(articles)

@app.route('/api/reminders')
def get_reminders():
    reminders = Reminder.find_all()
    return jsonify(reminders)

@app.route('/api/members')
def get_members():
    members = Member.find_all()
    return jsonify(members)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
