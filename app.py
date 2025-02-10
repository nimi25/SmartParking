from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, User, bcrypt
import urllib.parse

# Initialize Flask app
app = Flask(__name__)

# Securely encode the PostgreSQL password
password = urllib.parse.quote("Student@1484")

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:{password}@localhost:5432/smart_parking_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure key

# Initialize Database, Migrations, and Login Manager
db.init_app(app)
bcrypt.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirects to login page if user is not authenticated

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home Route
@app.route('/')
def home():
    return redirect(url_for('login'))

# User Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('login'))

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)  # Hash password before saving
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('login.html')

# Protected Dashboard Route (Only for Logged-in Users)
@app.route('/dashboard')
@login_required
def dashboard():
    return f"Welcome, {current_user.username}! This is your dashboard."

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
