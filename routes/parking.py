from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from models import db, ParkingSpot, Booking
from datetime import datetime
import re
import requests  # For making OSRM API requests

parking_bp = Blueprint('parking', __name__)

@parking_bp.route('/add_parking_spot', methods=['POST'])
@login_required
def add_parking_spot():
    """
    Saves a new ParkingSpot record to the DB based on form data.
    """
    # Check if user is indeed an owner
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    # Collect form data
    location = request.form.get('location')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    price = request.form.get('price')
    two_wheeler = request.form.get('two_wheeler_spaces', 0)
    four_wheeler = request.form.get('four_wheeler_spaces', 0)
    available_from = request.form.get('available_from')  # e.g. "06:00"
    available_to = request.form.get('available_to')      # e.g. "22:00"
    description = request.form.get('description')

    # Validate required fields
    if not location or not lat or not lng or not price:
        flash("Please provide location, lat/lng, and price.", "danger")
        return redirect(url_for('owner.parkingspace'))

    # Convert lat/lng/price
    try:
        lat = float(lat)
        lng = float(lng)
        price = float(price)
        two_wheeler = int(two_wheeler)
        four_wheeler = int(four_wheeler)
    except ValueError:
        flash("Invalid numerical inputs for lat/lng/price/spaces.", "danger")
        return redirect(url_for('owner.parkingspace'))

    # Convert times if provided
    from datetime import time
    from_time = None
    to_time = None
    if available_from:
        # e.g. "06:00"
        try:
            parts = available_from.split(':')
            from_time = time(int(parts[0]), int(parts[1]))
        except:
            flash("Invalid 'Available From' time format.", "danger")
            return redirect(url_for('owner.parkingspace'))
    if available_to:
        try:
            parts = available_to.split(':')
            to_time = time(int(parts[0]), int(parts[1]))
        except:
            flash("Invalid 'Available To' time format.", "danger")
            return redirect(url_for('owner.parkingspace'))

    # Create new ParkingSpot
    new_spot = ParkingSpot(
        owner_id=current_user.id,
        location=location,
        lat=lat,
        lng=lng,
        price=price,
        two_wheeler_spaces=two_wheeler,
        four_wheeler_spaces=four_wheeler,
        availability=True,  # new spots are available by default
        description=description or "",
        available_from=from_time,
        available_to=to_time
    )

    db.session.add(new_spot)
    db.session.commit()

    flash("New parking spot added successfully!", "success")
    return redirect(url_for('owner.parkingspace'))


@parking_bp.route('/update/<int:spot_id>', methods=['GET', 'POST'])
@login_required
def update_parking_spot(spot_id):
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('owner.owner_dashboard'))
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.owner_id != current_user.id:
        flash("You cannot update a spot you do not own.", "danger")
        return redirect(url_for('owner.owner_dashboard'))
    if request.method == 'POST':
        spot.location = request.form.get('location', spot.location)
        try:
            spot.price = float(request.form.get('price', spot.price))
        except (ValueError, TypeError):
            flash("Invalid price value.", "danger")
            return redirect(url_for('parking.update_parking_spot', spot_id=spot_id))

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

        db.session.commit()
        flash("Parking spot updated successfully!", "success")
        return redirect(url_for('owner.parkingspace'))
    return render_template('update_parking_spot.html', spot=spot)


@parking_bp.route('/delete/<int:spot_id>', methods=['POST'])
@login_required
def delete_parking_spot(spot_id):
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('owner.owner_dashboard'))

    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.owner_id != current_user.id:
        flash("You cannot delete a spot you do not own.", "danger")
        return redirect(url_for('owner.owner_dashboard'))

    active_bookings = [b for b in spot.booking if b.active]
    if active_bookings:
        flash("Cannot delete this spot as there is an active booking.", "danger")
        return redirect(url_for('owner.owner_dashboard'))

    try:
        db.session.delete(spot)
        db.session.commit()
        flash("Parking spot deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting spot: " + str(e), "danger")

    return redirect(url_for('owner.owner_dashboard'))


@parking_bp.route('/book/<int:spot_id>', methods=['POST'])
@login_required
def book_spot(spot_id):
    if session.get('role') != 'driver':
        flash("Only drivers can book spots.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    spot = ParkingSpot.query.get_or_404(spot_id)

    # Parse 2W/4W from form
    try:
        two_wheeler = int(request.form.get('two_wheeler', 0))
        four_wheeler = int(request.form.get('four_wheeler', 0))
    except ValueError:
        flash("Please enter valid numbers for spot counts.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    # Parse booking times
    booking_start = request.form.get('booking_start')
    booking_end = request.form.get('booking_end')
    try:
        booking_start_time = datetime.strptime(booking_start, "%H:%M").time()
        booking_end_time = datetime.strptime(booking_end, "%H:%M").time()
    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    # Check if booking times are within spot availability
    if spot.available_from and spot.available_to:
        if booking_start_time < spot.available_from or booking_end_time > spot.available_to:
            flash("Booking time must be within the available hours.", "danger")
            return redirect(url_for('dashboard.dashboard'))

    # Check if enough spaces remain
    if two_wheeler > (spot.two_wheeler_spaces or 0):
        flash("Not enough 2-wheeler spaces available.", "danger")
        return redirect(url_for('dashboard.dashboard'))
    if four_wheeler > (spot.four_wheeler_spaces or 0):
        flash("Not enough 4-wheeler spaces available.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    # Subtract from the spot's available spaces
    spot.two_wheeler_spaces = (spot.two_wheeler_spaces or 0) - two_wheeler
    spot.four_wheeler_spaces = (spot.four_wheeler_spaces or 0) - four_wheeler

    # If both 2W and 4W spaces are now 0 or less, mark spot as unavailable
    if (spot.two_wheeler_spaces <= 0) or (spot.four_wheeler_spaces <= 0):
        spot.availability = False

    # Determine booked vehicle type for convenience
    booked_vehicle_type = None
    if two_wheeler > 0 and four_wheeler == 0:
        booked_vehicle_type = "two_wheeler"
    elif two_wheeler == 0 and four_wheeler > 0:
        booked_vehicle_type = "four_wheeler"
    elif two_wheeler > 0 and four_wheeler > 0:
        booked_vehicle_type = "both"

    vehicle_number = request.form.get("vehicle_number")

    # Create new Booking record
    new_booking = Booking(
        user_id=current_user.id,
        spot_id=spot_id,
        two_wheeler=two_wheeler,
        four_wheeler=four_wheeler,
        booked_vehicle_type=booked_vehicle_type,
        start_time=booking_start_time,
        end_time=booking_end_time,
        active=True,
        vehicle_number=vehicle_number,
        status="Pending"
    )
    db.session.add(new_booking)
    print("After booking:", spot.two_wheeler_spaces, spot.four_wheeler_spaces, "=> availability?", spot.availability)
    if (spot.two_wheeler_spaces <= 0) and (spot.four_wheeler_spaces <= 0):
        spot.availability = False
        print(">>> Setting availability=False for", spot.location)
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
    spot.two_wheeler_spaces = (spot.two_wheeler_spaces or 0) + booking.two_wheeler
    spot.four_wheeler_spaces = (spot.four_wheeler_spaces or 0) + booking.four_wheeler
    spot.availability = True

    db.session.delete(booking)
    db.session.commit()
    flash("Booking cancelled.", "success")
    return redirect(url_for('dashboard.dashboard'))

@parking_bp.route('/direction/<int:spot_id>', methods=['GET'])
@login_required
def get_directions(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    driver_lat = request.args.get('lat', type=float)
    driver_lng = request.args.get('lng', type=float)
    if driver_lat is None or driver_lng is None:
        return jsonify({"error": "Driver location (lat, lng) is required"}), 400

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


