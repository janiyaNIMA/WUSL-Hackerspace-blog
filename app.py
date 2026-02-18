from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId
import os
import json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Import separated modules
from extensions import db, bcrypt, login_manager
from models import User, Project, Article, Reminder, Member, ContentBlock
from database import init_mongodb, seed_database

# Load .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-key-if-missing')

# --- SQLite Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'hackerspace.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)

# Initialize MongoDB
mongo_client, users_col = init_mongodb()

# Seed SQLite database
seed_database(app)

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
            user_data = users_col.find_one({"email": email})
            if user_data and bcrypt.check_password_hash(user_data['password'], password):
                user_obj = User(user_data)
                login_user(user_obj)
                print(f"✅ User {email} logged in successfully.")
                return redirect(url_for('index'))
            else:
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
                new_item = Article(
                    title=title, 
                    author=current_user.username,
                    author_id=current_user.id
                )
            else:
                new_item = Project(
                    title=title, 
                    color="#fdfaf6",
                    author_id=current_user.id
                )
            
            db.session.add(new_item)
            db.session.flush() # Get the ID for foreign keys

            # Create structured blocks
            for i, block_data in enumerate(blocks):
                new_block = ContentBlock(
                    article_id=new_item.id if content_type == 'news' else None,
                    project_id=new_item.id if content_type == 'project' else None,
                    type=block_data['type'],
                    sub_type=block_data['sub_type'],
                    value=block_data.get('value', ''),
                    sequence=i
                )
                db.session.add(new_block)

            db.session.commit()
            
            target_page = 'news' if content_type == 'news' else 'index'
            flash(f'{"Article" if content_type == "news" else "Project"} published successfully!')
            return redirect(url_for(target_page))
            
        except Exception as e:
            db.session.rollback()
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
        articles = Article.query.all()
        projects = Project.query.all()
    else:
        articles = Article.query.filter_by(author_id=current_user.id).all()
        projects = Project.query.filter_by(author_id=current_user.id).all()
        
    return render_template('manage_content.html', articles=articles, projects=projects)

@app.route('/edit-content/<type>/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_content(type, id):
    item = Article.query.get(id) if type == 'news' else Project.query.get(id)
    if not item:
        flash('Item not found.')
        return redirect(url_for('manage_content'))
        
    if item.author_id != current_user.id and not current_user.is_admin:
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
            
            item.title = title
            
            # Clear existing blocks and recreate
            ContentBlock.query.filter_by(article_id=item.id if type == 'news' else None, 
                                       project_id=item.id if type != 'news' else None).delete()
            
            for i, block_data in enumerate(blocks):
                new_block = ContentBlock(
                    article_id=item.id if type == 'news' else None,
                    project_id=item.id if type != 'news' else None,
                    type=block_data['type'],
                    sub_type=block_data['sub_type'],
                    value=block_data.get('value', ''),
                    sequence=i
                )
                db.session.add(new_block)
                
            db.session.commit()
            flash('Content updated successfully!')
            return redirect(url_for('manage_content'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating content: {e}')
            
    # Pass existing blocks as JSON list for the frontend editor
    blocks_list = [b.to_dict() for b in item.blocks]
    return render_template('create_article.html', 
                          item=item, 
                          content_type=type, 
                          existing_blocks=json.dumps(blocks_list))

@app.route('/toggle-visibility/<type>/<int:id>')
@login_required
def toggle_visibility(type, id):
    item = Article.query.get(id) if type == 'news' else Project.query.get(id)
    if not item:
        flash('Item not found.')
        return redirect(url_for('manage_content'))
        
    if item.author_id != current_user.id and not current_user.is_admin:
        flash('Permission denied.')
        return redirect(url_for('manage_content'))
        
    item.is_private = not item.is_private
    db.session.commit()
    flash('Visibility updated.')
    return redirect(url_for('manage_content'))

@app.route('/delete-content/<type>/<int:id>')
@login_required
def delete_content(type, id):
    item = Article.query.get(id) if type == 'news' else Project.query.get(id)
    if not item:
        flash('Item not found.')
        return redirect(url_for('manage_content'))
        
    if item.author_id != current_user.id and not current_user.is_admin:
        flash('Permission denied.')
        return redirect(url_for('manage_content'))
        
    db.session.delete(item)
    db.session.commit()
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
        users = list(users_col.find())
        return render_template('manage_users.html', users=users)
    except Exception as e:
        flash(f'Error fetching users: {e}')
        return redirect(url_for('index'))

# --- API Routes ---
@app.route('/api/projects')
def get_projects():
    # Only return public projects
    projects = Project.query.filter_by(is_private=False).all()
    return jsonify([p.to_dict() for p in projects])

@app.route('/api/articles')
def get_articles():
    # Only return public articles
    articles = Article.query.filter_by(is_private=False).all()
    return jsonify([a.to_dict() for a in articles])

@app.route('/api/reminders')
def get_reminders():
    return jsonify([r.to_dict() for r in Reminder.query.all()])

@app.route('/api/members')
def get_members():
    return jsonify([m.to_dict() for m in Member.query.all()])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
