import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, ParkingSpot, bcrypt  # Use ParkingSpot instead of ParkingSpace
import urllib.parse
from routes.parking import parking_bp  # ✅ Import directly from parking.py

# Initialize Flask app
app = Flask(__name__)

# Database Configuration
db_password = urllib.parse.quote("Student@1484")
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:{db_password}@localhost:5432/smart_parking_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Register Blueprints
app.register_blueprint(parking_bp, url_prefix="/parking")

# ✅ Registers parking routes
@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).filter_by(id=user_id).first()

if __name__ == "__main__":
    app.run(debug=True)

# Remove duplicate class definitions of User and ParkingSpot

# Routes start here...
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form.get("password")
        role = request.form['role']  # 'driver' or 'owner'

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('login'))

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') == 'driver':
        spots = ParkingSpot.query.filter_by(availability=True).all()
        return render_template('driver_dashboard.html', spots=spots)
    elif session.get('role') == 'owner':
        return render_template('owner_dashboard.html')
    return redirect(url_for('login'))

@app.route('/add_parking_spot', methods=['GET', 'POST'])
@login_required
def add_parking_spot():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        location = request.form['location']
        price = float(request.form['price'])
        availability = 'available' in request.form  # Checkbox for availability

        new_spot = ParkingSpot(
            location=location,
            price=price,
            availability=availability,
            owner_id=current_user.id
        )

        db.session.add(new_spot)
        db.session.commit()
        flash("Parking spot added successfully!", "success")
        return redirect(url_for('owner_dashboard'))  # Redirecting to owner_dashboard

    return render_template('add_parking_spot.html')

@app.route('/owner_dashboard')
@login_required
def owner_dashboard():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard'))

    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
    return render_template('owner_dashboard.html', spots=spots)

@app.route('/delete_parking_spot/<int:spot_id>', methods=['POST'])
@login_required
def delete_parking_spot(spot_id):
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard'))

    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.owner_id != current_user.id:
        flash("You cannot delete a spot you do not own.", "danger")
        return redirect(url_for('owner_dashboard'))

    db.session.delete(spot)
    db.session.commit()
    flash("Parking spot deleted successfully!", "success")
    return redirect(url_for('owner_dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
