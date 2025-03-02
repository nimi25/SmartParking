from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, ParkingSpot, User
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# Decorator to enforce admin-only access
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Unauthorized access!", "danger")
            return redirect(url_for('dashboard.dashboard'))
        return func(*args, **kwargs)
    return wrapper

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
        try:
            spot.two_wheeler_spaces = int(request.form.get('two_wheeler_spaces', spot.two_wheeler_spaces or 0))
            spot.four_wheeler_spaces = int(request.form.get('four_wheeler_spaces', spot.four_wheeler_spaces or 0))
        except ValueError:
            flash("Vehicle space counts must be integers.", "danger")
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
        return redirect(url_for('dashboard.dashboard'))
    return render_template('admin_edit_spot.html', spot=spot)

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
    return redirect(url_for('dashboard.dashboard'))

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
    return redirect(url_for('dashboard.dashboard'))
