import os
import re
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_migrate import Migrate
from flask_login import (
    LoginManager, login_user, login_required, logout_user, current_user
)
from models import db, User, ParkingSpot, bcrypt, Booking
from datetime import datetime

# 1. Load environment variables from .env file BEFORE using os.environ
load_dotenv()

# 2. Initialize Flask app
app = Flask(__name__)

# 3. Configuration using environment variables (with fallback defaults)
#    IMPORTANT: Use 127.0.0.1 to avoid IPv6 (::1) issues
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:student@127.0.0.1:5432/smart_parking_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key')

# Print the final DB URI to confirm it matches what you expect
print("Final DB URI in Flask config:", app.config['SQLALCHEMY_DATABASE_URI'])

# 4. Initialize extensions
db.init_app(app)       # Links the SQLAlchemy instance to this Flask app
bcrypt.init_app(app)   # If you want to use bcrypt features in your routes
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

        # Create the User WITHOUT passing password=...
        new_user = User(username=username, email=email, role=role)
        # Now set the password hash
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
        # Fetch filtered parking spots
        spots = ParkingSpot.query.all()
        print("✅ User is a driver.")  # Debugging

        # Ensure ParkingSpot is correctly referenced
        print("✅ Checking ParkingSpot query.")
        query = ParkingSpot.query.filter_by(availability=True)  # Initialize the query


        # Retrieve filter parameters from query string
        location = request.args.get('location', '')
        price_min = request.args.get('price_min', '')
        price_max = request.args.get('price_max', '')
        time_slot = request.args.get('time_slot', '')
        vehicle_type = request.args.get('vehicle_type', '')

        print(
            f"Filters - Location: {location}, Min Price: {price_min}, Max Price: {price_max}, Time Slot: {time_slot}, Vehicle Type: {vehicle_type}")

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


        # Debugging: Print the fetched spots
        print(f"Filtered Parking Spots: {spots}")

        return render_template('driver_dashboard.html', spots=spots)

    elif session.get('role') == 'owner':
        print("✅ User is an owner, redirecting.")
        return redirect(url_for('owner_dashboard'))

    print("❌ No valid session role. Redirecting to login.")
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

    # Check if spot is already booked
    if not spot.availability:
        flash("This spot is already booked.", "danger")
        return redirect(url_for('dashboard'))

    try:
        two_wheeler = int(request.form.get('two_wheeler', 0))
        four_wheeler = int(request.form.get('four_wheeler', 0))
    except ValueError:
        flash("Please enter valid numbers for spot counts.", "danger")
        return redirect(url_for('dashboard'))

    # Validate space availability
    if two_wheeler > spot.two_wheeler_spaces or four_wheeler > spot.four_wheeler_spaces:
        flash("Not enough parking spaces available.", "danger")
        return redirect(url_for('dashboard'))

    booking_start = request.form.get('booking_start')
    booking_end = request.form.get('booking_end')
    try:
        booking_start_time = datetime.strptime(booking_start, "%H:%M").time()
        booking_end_time = datetime.strptime(booking_end, "%H:%M").time()
    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
        return redirect(url_for('dashboard'))

    if spot.available_from and spot.available_to:
        if booking_start_time < spot.available_from or booking_end_time > spot.available_to:
            flash("Booking time must be within the available hours.", "danger")
            return redirect(url_for('dashboard'))

    try:
        # Create a booking record
        new_booking = Booking(
            user_id=current_user.id,
            spot_id=spot.id,
            two_wheeler=two_wheeler,
            four_wheeler=four_wheeler,
            start_time=booking_start_time,
            end_time=booking_end_time
        )
        db.session.add(new_booking)

        # Update spot status
        spot.availability = False
        spot.booked_by = current_user.id  # Add this line to track who booked

        db.session.commit()
        flash("Booking successful!", "success")

    except Exception as e:
        db.session.rollback()
        flash("An error occurred while booking the spot.", "danger")

    return redirect(url_for('dashboard'))


@app.route('/cancel_booking/<int:spot_id>', methods=['POST'])
@login_required
def cancel_booking(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)

    # Find the active booking for this spot
    booking = Booking.query.filter_by(spot_id=spot_id, active=True).first()

    if not booking:
        flash("No active booking found for this spot!", "danger")
        return redirect(url_for('dashboard'))

    try:
        # Check permissions
        if current_user.role == 'driver':
            if booking.user_id != current_user.id:
                flash("You can only cancel your own bookings!", "danger")
                return redirect(url_for('dashboard'))
        elif current_user.role == 'owner':
            if spot.owner_id != current_user.id:
                flash("You can only cancel bookings for your own spots!", "danger")
                return redirect(url_for('dashboard'))

        # Update the booking and spot
        booking.active = False
        spot.availability = True
        spot.booked_by = None  # Clear the booked_by field

        db.session.commit()
        flash("Booking canceled successfully!", "success")

    except Exception as e:
        db.session.rollback()
        flash("An error occurred while canceling the booking.", "danger")

    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
