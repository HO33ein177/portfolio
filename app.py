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


# Add this dictionary near your category_intros
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
    # Get all items, newest first
    items = PortfolioItem.query.order_by(desc(PortfolioItem.id)).all()

    categories = {}

    # Only calculate the categories for the interactive bottom grid
    for item in items:
        if item.category not in categories:
            categories[item.category] = item

    # Pass manual_category_previews to the template instead of calculating it
    return render_template(
        'portfolio.html',
        categories=categories,
        category_previews=manual_category_previews,
        intros=category_intros,
        active_page='portfolio'
    )


@app.route('/portfolio/<category_name>')
def portfolio_category(category_name):
    # Fetch all items that match the requested category
    items = PortfolioItem.query.filter_by(category=category_name).all()

    # Get the introduction text, or default to an empty string if not found
    intro = category_intros.get(category_name, '')

    return render_template('category.html', category_name=category_name, items=items, intro=intro,
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
    item.category = request.form['category'].strip()
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


# --- Main Execution ---
if __name__ == '__main__':
    # Make sure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

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
