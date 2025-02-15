import os
import re
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, ParkingSpot, bcrypt
import urllib.parse
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration using environment variables (with fallback defaults)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:1234@localhost:5432/smart_parking_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key')

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).filter_by(id=user_id).first()

# Routes start here...
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']  # 'driver' or 'owner'

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('login'))

        new_user = User(username=username, email=email, password=password, role=role)
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
            # Removed remember me functionality; user will not be remembered across sessions.
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
        query = ParkingSpot.query.filter_by(availability=True)

        # Retrieve filter parameters from the query string
        location = request.args.get('location', '')
        price_min = request.args.get('price_min', '')
        price_max = request.args.get('price_max', '')
        time_slot = request.args.get('time_slot', '')  # Expected format: "HH:MM-HH:MM"
        vehicle_type = request.args.get('vehicle_type', '')  # Expected: "" (any), "2", or "4"

        # Filter by location (case-insensitive)
        if location:
            query = query.filter(ParkingSpot.location.ilike(f"%{location}%"))

        # Filter by price range
        try:
            if price_min:
                query = query.filter(ParkingSpot.price >= float(price_min))
            if price_max:
                query = query.filter(ParkingSpot.price <= float(price_max))
        except ValueError:
            flash("Price values must be numbers.", "danger")

        # Filter by time slot
        if time_slot:
            try:
                start_time_str, end_time_str = time_slot.split('-')
                start_time = datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
                query = query.filter(ParkingSpot.available_from <= start_time,
                                     ParkingSpot.available_to >= end_time)
            except ValueError:
                flash("Invalid time slot format. Use HH:MM-HH:MM", "danger")

        # Filter by vehicle type
        if vehicle_type == '2':
            query = query.filter(ParkingSpot.two_wheeler_spaces > 0)
        elif vehicle_type == '4':
            query = query.filter(ParkingSpot.four_wheeler_spaces > 0)

        spots = query.all()
        return render_template('driver_dashboard.html', spots=spots)

    elif session.get('role') == 'owner':
        return redirect(url_for('owner_dashboard'))
    return redirect(url_for('login'))

# Endpoint to add a parking spot (Owner only)
@app.route('/add_parking_spot', methods=['GET', 'POST'])
@login_required
def add_parking_spot():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        location = request.form['location']
        try:
            price = float(request.form['price'])
        except ValueError:
            flash("Price must be a number.", "danger")
            return redirect(url_for('add_parking_spot'))
        # Checkbox: if checked, availability is True; otherwise, False.
        availability = 'availability' in request.form

        # New fields: Google Maps link, vehicle space counts, description, available timings
        google_maps_link = request.form.get('google_maps_link', '')
        # Extract src attribute if the provided link is an iframe embed code
        if google_maps_link.strip().startswith("<iframe"):
            match = re.search(r'src="([^"]+)"', google_maps_link)
            if match:
                google_maps_link = match.group(1)

        try:
            two_wheeler_spaces = int(request.form.get('two_wheeler_spaces', 0))
            four_wheeler_spaces = int(request.form.get('four_wheeler_spaces', 0))
        except ValueError:
            flash("Vehicle space counts must be integers.", "danger")
            return redirect(url_for('add_parking_spot'))
        description = request.form.get('description', '')

        available_from_str = request.form.get('available_from', '')
        available_to_str = request.form.get('available_to', '')
        available_from = None
        available_to = None
        try:
            if available_from_str:
                available_from = datetime.strptime(available_from_str, "%H:%M").time()
            if available_to_str:
                available_to = datetime.strptime(available_to_str, "%H:%M").time()
        except ValueError:
            flash("Invalid time format. Please use HH:MM.", "danger")
            return redirect(url_for('add_parking_spot'))

        new_spot = ParkingSpot(
            location=location,
            price=price,
            availability=availability,
            owner_id=current_user.id,
            google_maps_link=google_maps_link,
            two_wheeler_spaces=two_wheeler_spaces,
            four_wheeler_spaces=four_wheeler_spaces,
            description=description,
            available_from=available_from,
            available_to=available_to
        )

        db.session.add(new_spot)
        db.session.commit()
        flash("Parking spot added successfully!", "success")
        return redirect(url_for('owner_dashboard'))

    return render_template('add_parking_spot.html')

# Endpoint to update a parking spot (Owner only)
@app.route('/update_parking_spot/<int:spot_id>', methods=['GET', 'POST'])
@login_required
def update_parking_spot(spot_id):
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard'))

    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.owner_id != current_user.id:
        flash("You cannot update a spot you do not own.", "danger")
        return redirect(url_for('owner_dashboard'))

    if request.method == 'POST':
        spot.location = request.form.get('location', spot.location)
        try:
            spot.price = float(request.form.get('price', spot.price))
        except (ValueError, TypeError):
            flash("Invalid price value.", "danger")
            return redirect(url_for('update_parking_spot', spot_id=spot_id))
        spot.availability = 'availability' in request.form

        # Update the Google Maps link and extract src if needed
        google_maps_link = request.form.get('google_maps_link', spot.google_maps_link)
        if google_maps_link.strip().startswith("<iframe"):
            match = re.search(r'src="([^"]+)"', google_maps_link)
            if match:
                google_maps_link = match.group(1)
        spot.google_maps_link = google_maps_link

        try:
            spot.two_wheeler_spaces = int(request.form.get('two_wheeler_spaces', spot.two_wheeler_spaces or 0))
            spot.four_wheeler_spaces = int(request.form.get('four_wheeler_spaces', spot.four_wheeler_spaces or 0))
        except ValueError:
            flash("Vehicle space counts must be integers.", "danger")
            return redirect(url_for('update_parking_spot', spot_id=spot_id))
        spot.description = request.form.get('description', spot.description)

        available_from_str = request.form.get('available_from', '')
        available_to_str = request.form.get('available_to', '')
        try:
            if available_from_str:
                spot.available_from = datetime.strptime(available_from_str, "%H:%M").time()
            if available_to_str:
                spot.available_to = datetime.strptime(available_to_str, "%H:%M").time()
        except ValueError:
            flash("Invalid time format. Please use HH:MM.", "danger")
            return redirect(url_for('update_parking_spot', spot_id=spot_id))

        db.session.commit()
        flash("Parking spot updated successfully!", "success")
        return redirect(url_for('owner_dashboard'))

    return render_template('update_parking_spot.html', spot=spot)

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

@app.route('/test-db')
def test_db():
    try:
        db.session.execute("SELECT 1")
        return "Database connected successfully!"
    except Exception as e:
        return f"Database connection failed: {str(e)}", 500


@app.route('/book/<int:spot_id>', methods=['POST'])
@login_required
def book_spot(spot_id):
    # Only drivers can book
    if session.get('role') != 'driver':
        flash("Only drivers can book spots.", "danger")
        return redirect(url_for('dashboard'))

    spot = ParkingSpot.query.get_or_404(spot_id)

    try:
        two_wheeler = int(request.form.get('two_wheeler', 0))
        four_wheeler = int(request.form.get('four_wheeler', 0))
    except ValueError:
        flash("Please enter valid numbers for spot counts.", "danger")
        return redirect(url_for('dashboard'))

    booking_start = request.form.get('booking_start')
    booking_end = request.form.get('booking_end')
    try:
        booking_start_time = datetime.strptime(booking_start, "%H:%M").time()
        booking_end_time = datetime.strptime(booking_end, "%H:%M").time()
    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
        return redirect(url_for('dashboard'))

    # Ensure the booking times are within the spot's available times
    if spot.available_from and spot.available_to:
        if booking_start_time < spot.available_from or booking_end_time > spot.available_to:
            flash("Booking time must be within the available hours.", "danger")
            return redirect(url_for('dashboard'))

    # (Optional) Save the booking information in the database here.

    flash("Booking successful!", "success")
    return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.run(debug=True)
