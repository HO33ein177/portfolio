import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# 2. Join the base directory with your database filename
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'portfolio.db')


# Get the credentials from the .env file
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
admin_raw_password = os.getenv('ADMIN_PASSWORD')

# Hash the password after loading it
ADMIN_PASSWORD_HASH = generate_password_hash(admin_raw_password)

# --- Login Required Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Images will be saved here
app.config['SECRET_KEY'] = 'super-secret-key'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)


# --- Database Model ---
class PortfolioItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'photography' or 'academic'
    filename = db.Column(db.String(100), nullable=False)


# Initialize Database
with app.app_context():
    db.create_all()


# --- Routes ---
@app.route('/')
def home():
    photo_page = request.args.get('photo_page', 1, type=int)
    acad_page = request.args.get('acad_page', 1, type=int)

    photos = PortfolioItem.query.filter_by(category='photography').paginate(page=photo_page, per_page=6)
    academic_items = PortfolioItem.query.filter_by(category='academic').paginate(page=acad_page, per_page=6)

    return render_template('index.html', photos=photos, academic_items=academic_items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, send them straight to admin
    if 'logged_in' in session:
        return redirect(url_for('admin'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if username matches and password is correct
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['logged_in'] = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        file = request.files['file']

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Save to database
            new_item = PortfolioItem(title=title, category=category, filename=filename)
            db.session.add(new_item)
            db.session.commit()
            return redirect(url_for('admin'))

    all_items = PortfolioItem.query.order_by(PortfolioItem.id.desc()).all()
    return render_template('admin.html', items=all_items)


@app.route('/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    # 1. Retrieve the item from the database
    item = PortfolioItem.query.get_or_404(item_id)

    # 2. Construct the file path and delete the file from the server
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], item.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # 3. Delete the record from the database
    db.session.delete(item)
    db.session.commit()

    # 4. Redirect back to the admin panel
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
