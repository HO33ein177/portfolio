# app.py
from collections import defaultdict
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import desc

# --- App Configuration ---
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_secret_key_for_development')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'portfolio.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit
app.config['VIDEO_UPLOAD_FOLDER'] = os.path.join(basedir, 'static/videos')
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024  # 100 MB for videos
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


class PortfolioItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(100), nullable=False)

# --- Add this new model after the PortfolioItem class ---
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Public Facing Routes ---

@app.route('/')
def home():
    """Renders the home/landing page."""
    return render_template('index.html', active_page='home')


category_intros = {
    'Product': 'Showcasing products with clarity and creative lighting.',
    'Lifestyle': 'Capturing authentic moments and natural storytelling.',
    'Branding': 'Elevating your brand identity through professional imagery.',
    'Event': 'Documenting the atmosphere and key moments of your special events.',
    'Sports': 'Action-packed sports photography capturing peak performance.',
    'Fashion': 'Highlighting style, apparel, and trends with striking editorial and commercial photography.',
    'Architecture': 'Capturing the design, structure, and aesthetic beauty of interior and exterior spaces.',
    'Content': 'Creating engaging, high-quality visual content tailored for social media and digital platforms.',
    'Food': 'Mouth-watering culinary photography that emphasizes texture, color, and beautiful presentation.',
    'Industrial': 'Showcasing the scale, processes, and technology of manufacturing and industrial environments.'
}

# Map form values → stored category name (must match manual_category_previews keys)
category_name_map = {
    'product': 'Product',
    'lifestyle': 'Lifestyle',
    'branding': 'Branding',
    'event': 'Event',
    'sport': 'Sports',          # note: plural!
    'food': 'Food',
    'fashion': 'Fashion',
    'industrial': 'Industrial',
    'architecture': 'Architecture',
    'content': 'Content'
}

manual_category_previews = {
    'Product': ['images/img-product-1.jpeg', 'images/img-product-2.jpeg'],
    'Lifestyle': ['images/img-lifestyle-1.jpeg', 'images/img-lifestyle-2.jpeg'],
    'Branding': ['images/img-branding-1.jpeg', 'images/img-branding-2.jpeg'],
    'Event': ['images/img-event-1.jpeg', 'images/img-event-2.jpeg'],
    'Sports': ['images/img-sport-1.jpeg', 'images/img-sport-2.jpeg'],
    'Fashion': ['images/img-fashion-1.jpeg', 'images/img-fashion-2.jpeg'],
    'Architecture': ['images/img-arch-1.jpeg', 'images/img-arch-2.jpeg'],
    'Content': ['images/img-content-1.jpeg', 'images/img-content-2.jpeg'],
    'Food': ['images/img-food-1.jpeg', 'images/img-food-2.jpeg'],
    'Industrial': ['images/img-industrial-1.jpeg', 'images/img-industrial-2.jpeg']
}


@app.route('/portfolio')
def portfolio():
    # 1. Get all uploaded items
    items = PortfolioItem.query.order_by(desc(PortfolioItem.id)).all()
    videos = Video.query.order_by(desc(Video.id)).all()   # <-- add this line

    # 2. Create the dictionary for uploaded category cards
    categories_dict = {}
    for item in items:
        if item.category not in categories_dict:
            categories_dict[item.category] = item

    # 4. Pass EVERYTHING to the template
    return render_template(
        'portfolio.html',
        categories=categories_dict,
        items=items,                       # <--- Missing dynamic items
        category_previews=manual_category_previews, # <--- Missing static previews
        intros=category_intros,
        videos=videos,
        active_page='portfolio'
    )


@app.route('/portfolio/<category_name>')
def portfolio_category(category_name):
    # Get the stored category name from the mapping
    stored_category = category_name_map.get(category_name)
    if not stored_category:
        # Optionally handle 404 or fallback
        flash('Category not found', 'danger')
        return redirect(url_for('portfolio'))

    items = PortfolioItem.query.filter_by(category=stored_category).all()
    intro = category_intros.get(stored_category, '')

    return render_template('category.html',
                           category_name=stored_category,
                           items=items,
                           intro=intro,
                           active_page='portfolio')

@app.route('/about')
def about():
    """Renders the about page."""
    return render_template('about.html', active_page='about')


@app.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template('contact.html', active_page='contact')


# Placeholder routes for Reviews and News
@app.route('/reviews')
def reviews():
    """Renders the reviews page."""
    return render_template('reviews.html', active_page='reviews')


@app.route('/news')
def news():
    """Renders the news page."""
    return render_template('news.html', active_page='news')


# --- Admin & Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/admin')
@login_required
def admin():
    items = PortfolioItem.query.order_by(desc(PortfolioItem.id)).all()
    return render_template('admin.html', items=items)


@app.route('/add', methods=['POST'])
@login_required
def add_item():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('admin'))

    file = request.files['file']
    title = request.form['title']
    category = request.form['category'].strip()
    category = category_name_map.get(category, category)  # add this line

    if file.filename == '' or not title or not category:
        flash('Missing file, title, or category', 'danger')
        return redirect(url_for('admin'))

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_item = PortfolioItem(title=title, category=category, filename=filename)
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!', 'success')

    return redirect(url_for('admin'))


@app.route('/edit/<int:item_id>', methods=['POST'])
@login_required
def edit_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    item.title = request.form['title']

    # Normalize category using the mapping
    category_raw = request.form['category'].strip()
    item.category = category_name_map.get(category_raw, category_raw)

    db.session.commit()
    flash('Item updated successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)

    # Optional: Delete the file from the filesystem
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], item.filename))
    except OSError as e:
        flash(f"Error deleting file: {e}", "danger")

    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/videos')
@login_required
def admin_videos():
    videos = Video.query.order_by(desc(Video.id)).all()
    return render_template('admin_videos.html', videos=videos)


@app.route('/add_video', methods=['POST'])
@login_required
def add_video():
    if 'video' not in request.files:
        flash('No video file', 'danger')
        return redirect(url_for('admin_videos'))

    file = request.files['video']
    title = request.form['title']

    if file.filename == '' or not title:
        flash('Missing video or title', 'danger')
        return redirect(url_for('admin_videos'))

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], filename))
        new_video = Video(title=title, filename=filename)
        db.session.add(new_video)
        db.session.commit()
        flash('Video added successfully!', 'success')

    return redirect(url_for('admin_videos'))


@app.route('/delete_video/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    try:
        os.remove(os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], video.filename))
    except OSError as e:
        flash(f"Error deleting file: {e}", "danger")
    db.session.delete(video)
    db.session.commit()
    flash('Video deleted successfully!', 'success')
    return redirect(url_for('admin_videos'))


# --- Main Execution ---
if __name__ == '__main__':
    # Make sure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['VIDEO_UPLOAD_FOLDER']):
        os.makedirs(app.config['VIDEO_UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
        # Create a default user if none exists
        if not User.query.filter_by(username='admin').first():
            hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
            new_user = User(username='admin', password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            print("Default admin user created with password 'admin'. Please change this.")

    app.run(debug=True)
