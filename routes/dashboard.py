from flask import Blueprint, render_template, session, redirect, url_for, flash
from flask_login import login_required, current_user
from models import ParkingSpot

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def dashboard():
    role = session.get('role')

    if role == 'driver':
        spots = ParkingSpot.query.filter_by(availability=True).all()
        return render_template('driver_dashboard.html', spots=spots)
    elif role == 'owner':
        spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
        return render_template('owner_dashboard.html', spots=spots)

    flash("User role not recognized. Please log in again.", "warning")
    return redirect(url_for('auth.login'))
