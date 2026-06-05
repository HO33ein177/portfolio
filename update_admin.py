# update_admin.py
from app import app, db, User
from werkzeug.security import generate_password_hash

# Your new admin credentials
NEW_USERNAME = 'FarnazSydney1774519'  # Replace with your desired username
NEW_PASSWORD = '451990177'  # Replace with your desired password

with app.app_context():
    # Find the existing admin user (e.g., by the old username)
    admin_user = User.query.filter_by(username='admin').first()

    if admin_user:
        admin_user.username = NEW_USERNAME
        admin_user.password = generate_password_hash(NEW_PASSWORD)
        db.session.commit()
        print(f"Admin user updated! New username: {NEW_USERNAME}")
    else:
        print("Admin user not found.")