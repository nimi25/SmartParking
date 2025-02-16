from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, ParkingSpot
from datetime import datetime
import re

parking_bp = Blueprint('parking', __name__)

@parking_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_parking_spot():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))
    if request.method == 'POST':
        location = request.form['location']
        try:
            price = float(request.form['price'])
        except ValueError:
            flash("Price must be a number.", "danger")
            return redirect(url_for('parking.add_parking_spot'))
        availability = 'availability' in request.form
        google_maps_link = request.form.get('google_maps_link', '')
        if google_maps_link.strip().startswith("<iframe"):
            match = re.search(r'src="([^"]+)"', google_maps_link)
            if match:
                google_maps_link = match.group(1)
        try:
            two_wheeler_spaces = int(request.form.get('two_wheeler_spaces', 0))
            four_wheeler_spaces = int(request.form.get('four_wheeler_spaces', 0))
        except ValueError:
            flash("Vehicle space counts must be integers.", "danger")
            return redirect(url_for('parking.add_parking_spot'))
        description = request.form.get('description', '')
        available_from = None
        available_to = None
        try:
            available_from_str = request.form.get('available_from', '')
            available_to_str = request.form.get('available_to', '')
            if available_from_str:
                available_from = datetime.strptime(available_from_str, "%H:%M").time()
            if available_to_str:
                available_to = datetime.strptime(available_to_str, "%H:%M").time()
        except ValueError:
            flash("Invalid time format. Use HH:MM.", "danger")
            return redirect(url_for('parking.add_parking_spot'))
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
        return redirect(url_for('dashboard.dashboard'))
    return render_template('add_parking_spot.html')


@parking_bp.route('/update/<int:spot_id>', methods=['GET', 'POST'])
@login_required
def update_parking_spot(spot_id):
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.owner_id != current_user.id:
        flash("You cannot update a spot you do not own.", "danger")
        return redirect(url_for('dashboard.dashboard'))
    if request.method == 'POST':
        spot.location = request.form.get('location', spot.location)
        try:
            spot.price = float(request.form.get('price', spot.price))
        except (ValueError, TypeError):
            flash("Invalid price value.", "danger")
            return redirect(url_for('parking.update_parking_spot', spot_id=spot_id))
        spot.availability = 'availability' in request.form
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
            return redirect(url_for('parking.update_parking_spot', spot_id=spot_id))
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
            return redirect(url_for('parking.update_parking_spot', spot_id=spot_id))
        db.session.commit()
        flash("Parking spot updated successfully!", "success")
        return redirect(url_for('dashboard.dashboard'))
    return render_template('update_parking_spot.html', spot=spot)


@parking_bp.route('/delete/<int:spot_id>', methods=['POST'])
@login_required
def delete_parking_spot(spot_id):
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.owner_id != current_user.id:
        flash("You cannot delete a spot you do not own.", "danger")
        return redirect(url_for('dashboard.dashboard'))
    db.session.delete(spot)
    db.session.commit()
    flash("Parking spot deleted successfully!", "success")
    return redirect(url_for('dashboard.dashboard'))


@parking_bp.route('/book/<int:spot_id>', methods=['POST'])
@login_required
def book_spot(spot_id):
    if session.get('role') != 'driver':
        flash("Only drivers can book spots.", "danger")
        return redirect(url_for('dashboard.dashboard'))
    spot = ParkingSpot.query.get_or_404(spot_id)
    try:
        two_wheeler = int(request.form.get('two_wheeler', 0))
        four_wheeler = int(request.form.get('four_wheeler', 0))
    except ValueError:
        flash("Please enter valid numbers for spot counts.", "danger")
        return redirect(url_for('dashboard.dashboard'))
    booking_start = request.form.get('booking_start')
    booking_end = request.form.get('booking_end')
    try:
        booking_start_time = datetime.strptime(booking_start, "%H:%M").time()
        booking_end_time = datetime.strptime(booking_end, "%H:%M").time()
    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
        return redirect(url_for('dashboard.dashboard'))
    if spot.available_from and spot.available_to:
        if booking_start_time < spot.available_from or booking_end_time > spot.available_to:
            flash("Booking time must be within the available hours.", "danger")
            return redirect(url_for('dashboard.dashboard'))
    # Booking logic (mark spot as booked, optionally record booking details)
    spot.availability = False
    # Optionally: spot.booked_by = current_user.id (if such a field exists)
    db.session.commit()
    flash("Spot booked successfully!", "success")
    return redirect(url_for('dashboard.dashboard'))


@parking_bp.route('/cancel_booking/<int:spot_id>', methods=['POST'])
@login_required
def cancel_booking(spot_id):
    # Implement cancellation logic here.
    flash("Booking cancelled.", "success")
    return redirect(url_for('dashboard.dashboard'))
