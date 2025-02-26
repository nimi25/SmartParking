from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from models import db, ParkingSpot, Booking
from datetime import datetime
import re
import requests  # NEW: For making OSRM API requests

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

        # Read latitude and longitude from hidden fields
        try:
            lat = float(request.form['lat'])
            lng = float(request.form['lng'])
        except (ValueError, KeyError):
            flash("Could not determine location coordinates.", "danger")
            return redirect(url_for('parking.add_parking_spot'))

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

        # NEW: Always set availability to True so the spot is visible to drivers
        new_spot = ParkingSpot(
            location=location,
            price=price,
            lat=lat,
            lng=lng,
            owner_id=current_user.id,
            availability=True,
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

        # Update lat and lng from hidden fields
        try:
            spot.lat = float(request.form['lat'])
            spot.lng = float(request.form['lng'])
        except (ValueError, KeyError):
            flash("Invalid location coordinates.", "danger")
            return redirect(url_for('parking.update_parking_spot', spot_id=spot_id))

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

        # Do not change availability; leave it as is.
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

    active_bookings = [b for b in spot.booking if b.active]
    if active_bookings:
        flash("Cannot delete this spot as there is an active booking.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    try:
        db.session.delete(spot)
        db.session.commit()
        flash("Parking spot deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting spot: " + str(e), "danger")

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

    if two_wheeler > (spot.two_wheeler_spaces or 0):
        flash("Not enough 2-wheeler spaces available.", "danger")
        return redirect(url_for('dashboard.dashboard'))
    if four_wheeler > (spot.four_wheeler_spaces or 0):
        flash("Not enough 4-wheeler spaces available.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    # Subtract the booked spaces from the available count
    spot.two_wheeler_spaces = (spot.two_wheeler_spaces or 0) - two_wheeler
    spot.four_wheeler_spaces = (spot.four_wheeler_spaces or 0) - four_wheeler

    booked_vehicle_type = None
    if two_wheeler > 0 and four_wheeler == 0:
        booked_vehicle_type = "two_wheeler"
    elif two_wheeler == 0 and four_wheeler > 0:
        booked_vehicle_type = "four_wheeler"
    elif two_wheeler > 0 and four_wheeler > 0:
        booked_vehicle_type = "both"

    new_booking = Booking(
        user_id=current_user.id,
        spot_id=spot_id,
        two_wheeler=two_wheeler,
        four_wheeler=four_wheeler,
        booked_vehicle_type=booked_vehicle_type,
        start_time=booking_start,
        end_time=booking_end,
        active=True
    )
    db.session.add(new_booking)
    db.session.commit()
    flash("Spot booked successfully!", "success")
    return redirect(url_for('dashboard.dashboard'))


@parking_bp.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash("You cannot cancel a booking you did not make.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    spot = ParkingSpot.query.get(booking.spot_id)
    # Add the booked spaces back to the parking spot
    spot.two_wheeler_spaces = (spot.two_wheeler_spaces or 0) + booking.two_wheeler
    spot.four_wheeler_spaces = (spot.four_wheeler_spaces or 0) + booking.four_wheeler
    spot.availability = True  # Mark as available since the booking is cancelled

    db.session.delete(booking)
    db.session.commit()
    flash("Booking cancelled.", "success")
    return redirect(url_for('dashboard.dashboard'))


# NEW: Route to fetch directions from driver's location to a parking spot using OSRM
@parking_bp.route('/direction/<int:spot_id>', methods=['GET'])
@login_required
def get_directions(spot_id):
    """
    Expects query parameters 'lat' and 'lng' representing the driver's current location.
    Returns JSON containing the route details from OSRM.
    """
    spot = ParkingSpot.query.get_or_404(spot_id)
    driver_lat = request.args.get('lat', type=float)
    driver_lng = request.args.get('lng', type=float)
    if driver_lat is None or driver_lng is None:
        return jsonify({"error": "Driver location (lat, lng) is required"}), 400

    # Build OSRM API URL
    osrm_url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{driver_lng},{driver_lat};{spot.lng},{spot.lat}"
        f"?overview=full&geometries=geojson"
    )
    response = requests.get(osrm_url)
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch route from OSRM"}), 500

    data = response.json()
    return jsonify(data)
