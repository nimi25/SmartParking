from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, ParkingSpot, User, ParkingSpace, Booking, PaymentDetails
from datetime import datetime
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


# Decorator to enforce admin-only access
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Unauthorized access!", "danger")
            return redirect(url_for('dashboard.driver_dashboard'))
        return func(*args, **kwargs)

    return wrapper


# Admin dashboard route
@admin_bp.route('/', methods=['GET'])
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')


# User Management page
@admin_bp.route('/user_management', methods=['GET'])
@login_required
@admin_required
def user_management():
    users = User.query.all()
    return render_template('admin_user_management.html', users=users)


# Parking Management page
@admin_bp.route('/parking_management', methods=['GET'])
@login_required
@admin_required
def parking_management():
    spots = ParkingSpot.query.all()
    return render_template('admin_parking_management.html', spots=spots)


# Reports page with updated booking metrics
@admin_bp.route('/reports', methods=['GET'])
@login_required
@admin_required
def reports():
    total_users = User.query.count()
    total_spots = ParkingSpot.query.count()
    available_spots = ParkingSpot.query.filter_by(availability=True).count()

    # Calculate booked spots as the count of distinct parking spaces with active bookings
    booked_spots = db.session.query(Booking.parking_space_id) \
        .filter_by(active=True) \
        .distinct() \
        .count()

    # Total active booking records
    total_bookings = Booking.query.filter_by(active=True).count()

    # Revenue calculation (in rupees)
    revenue = db.session.query(func.sum(ParkingSpot.price)) \
                  .join(ParkingSpace, ParkingSpace.parking_spot_id == ParkingSpot.id) \
                  .join(Booking, Booking.parking_space_id == ParkingSpace.id) \
                  .filter(Booking.active == True) \
                  .scalar() or 0

    return render_template(
        'admin_reports.html',
        total_users=total_users,
        total_spots=total_spots,
        available_spots=available_spots,
        booked_spots=booked_spots,
        total_bookings=total_bookings,
        revenue=revenue
    )


# Analytics page
@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # Calculate the number of booked parking spaces (distinct parking_space IDs with an active booking)
    booked_spots = db.session.query(Booking.parking_space_id) \
        .filter_by(active=True) \
        .distinct() \
        .count()

    total_bookings = Booking.query.filter_by(active=True).count()
    # Example revenue calculation (adjust this logic as needed)
    revenue = db.session.query(db.func.sum(ParkingSpot.price)).scalar() or 0
    total_payment_details = PaymentDetails.query.count()

    return render_template(
        'admin_analytics.html',
        booked_spots=booked_spots,
        total_bookings=total_bookings,
        revenue=revenue,
        total_payment_details=total_payment_details
    )


# Add New User route
@admin_bp.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')  # Capture the role from the form

        if not username or not email or not password or not role:
            flash("One or more fields are missing.", "danger")
            return redirect(url_for('admin.add_user'))

        if role not in ['admin', 'owner', 'driver']:
            flash("Invalid role selected. Please try again.", "danger")
            return redirect(url_for('admin.user_management'))

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("User added successfully!", "success")
        return redirect(url_for('admin.user_management'))

    return render_template('admin_add_user.html')


# Edit Parking Spot route
@admin_bp.route('/edit_spot/<int:spot_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    if request.method == 'POST':
        spot.location = request.form.get('location', spot.location)
        try:
            spot.price = float(request.form.get('price', spot.price))
        except (ValueError, TypeError):
            flash("Invalid price value.", "danger")
            return redirect(url_for('admin.edit_spot', spot_id=spot_id))
        try:
            spot.lat = float(request.form.get('lat', spot.lat))
            spot.lng = float(request.form.get('lng', spot.lng))
        except (ValueError, KeyError):
            flash("Invalid location coordinates.", "danger")
            return redirect(url_for('admin.edit_spot', spot_id=spot_id))
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
            return redirect(url_for('admin.edit_spot', spot_id=spot_id))
        db.session.commit()
        flash("Parking spot updated successfully.", "success")
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin_edit_spot.html', spot=spot)


# Delete Parking Spot route
@admin_bp.route('/delete_spot/<int:spot_id>', methods=['POST'])
@login_required
@admin_required
def delete_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    try:
        db.session.delete(spot)
        db.session.commit()
        flash("Parking spot deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting spot: " + str(e), "danger")
    return redirect(url_for('admin.admin_dashboard'))


# Delete User route
@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting user: " + str(e), "danger")
    return redirect(url_for('admin.admin_dashboard'))


# Delete Parking Space route
@admin_bp.route('/delete_space/<int:space_id>', methods=['POST'], endpoint="delete_space")
@login_required
@admin_required
def delete_space(space_id):
    space = ParkingSpace.query.get_or_404(space_id)
    spot_id = space.parking_spot_id  # Retrieve parent spot id for redirection
    try:
        db.session.delete(space)
        db.session.commit()
        flash("Parking space deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting parking space: " + str(e), "danger")
    return redirect(url_for('admin.edit_spot', spot_id=spot_id))
