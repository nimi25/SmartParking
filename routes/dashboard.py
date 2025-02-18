from flask import Blueprint, render_template, session, redirect, url_for, flash
from flask_login import login_required, current_user
from models import ParkingSpot, Booking

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'driver':
        available_spots = ParkingSpot.query.all()
        booked_spots = Booking.query.filter_by(user_id=current_user.id).all()
        return render_template('driver_dashboard.html', available_spots=available_spots, booked_spots=booked_spots)
    elif role == 'owner':
        spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
        return render_template('owner_dashboard.html', spots=spots)
    flash("User role not recognized. Please log in again.", "warning")
    return redirect(url_for('auth.login'))
