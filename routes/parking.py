import json  # For JSON handling
import uuid  # For generating unique session IDs
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from models import db, ParkingSpot, Booking, ParkingSpace
from datetime import datetime, time
import requests  # For OSRM API requests

parking_bp = Blueprint('parking', __name__)

@parking_bp.route('/add_parking_spot_form', methods=['GET'])
@login_required
def add_parking_spot_form():
    return render_template('add_parking_spot.html')

@parking_bp.route('/add_parking_spot', methods=['POST'])
@login_required
def add_parking_spot():
    location = request.form.get('location')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    price = request.form.get('price')
    spaces_data = request.form.get('spaces_data')
    if spaces_data:
        try:
            spaces_list = json.loads(spaces_data)
            two_wheeler = sum(1 for s in spaces_list if s.get("vehicle_type") == "2W")
            four_wheeler = sum(1 for s in spaces_list if s.get("vehicle_type") == "4W")
        except Exception as e:
            flash("Error processing spaces data.", "danger")
            return redirect(url_for('owner.parkingspace'))
    else:
        two_wheeler = int(request.form.get('two_wheeler_spaces', 0))
        four_wheeler = int(request.form.get('four_wheeler_spaces', 0))
    available_from = request.form.get('available_from')  # e.g. "06:00"
    available_to = request.form.get('available_to')      # e.g. "22:00"
    description = request.form.get('description')

    if not location or not lat or not lng or not price:
        flash("Please provide location, lat/lng, and price.", "danger")
        return redirect(url_for('owner.parkingspace'))
    try:
        lat = float(lat)
        lng = float(lng)
        price = float(price)
    except ValueError:
        flash("Invalid numerical inputs for lat/lng/price.", "danger")
        return redirect(url_for('owner.parkingspace'))

    from_time = None
    to_time = None
    if available_from:
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

    new_spot = ParkingSpot(
        owner_id=current_user.id,
        location=location,
        lat=lat,
        lng=lng,
        price=price,
        availability=True,
        description=description or "",
        available_from=from_time,
        available_to=to_time
    )
    db.session.add(new_spot)
    db.session.commit()

    for i in range(1, two_wheeler + 1):
        space = ParkingSpace(
            parking_spot_id=new_spot.id,
            vehicle_type="2W",
            sub_spot_number=i,
            status="available"
        )
        db.session.add(space)
    for i in range(1, four_wheeler + 1):
        space = ParkingSpace(
            parking_spot_id=new_spot.id,
            vehicle_type="4W",
            sub_spot_number=i,
            status="available"
        )
        db.session.add(space)
    db.session.commit()

    flash("New parking spot added successfully!", "success")
    return redirect(url_for('owner.parkingspace'))

@parking_bp.route('/update/<int:spot_id>', methods=['POST'])
@login_required
def update_parking_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.owner_id != current_user.id:
        flash("You cannot update a spot you do not own.", "danger")
        return redirect(url_for('owner.parkingspace'))
    spot.location = request.form.get('location', spot.location)
    try:
        spot.price = float(request.form.get('price', spot.price))
    except (ValueError, TypeError):
        flash("Invalid price value.", "danger")
        return redirect(url_for('owner.parkingspace'))
    try:
        spot.lat = float(request.form['lat'])
        spot.lng = float(request.form['lng'])
    except (ValueError, KeyError):
        flash("Invalid location coordinates.", "danger")
        return redirect(url_for('owner.parkingspace'))
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
        return redirect(url_for('owner.parkingspace'))
    db.session.commit()
    flash("Parking spot updated successfully!", "success")
    return redirect(url_for('owner.parkingspace'))

@parking_bp.route('/delete/<int:spot_id>', methods=['POST'])
@login_required
def delete_parking_spot(spot_id):
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('owner.parkingspace'))
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.owner_id != current_user.id:
        flash("You cannot delete a spot you do not own.", "danger")
        return redirect(url_for('owner.parkingspace'))
    active_bookings = []
    for space in spot.spaces:
        active_bookings.extend([b for b in space.bookings if b.active])
    if active_bookings:
        flash("Cannot delete this spot as there is an active booking.", "danger")
        return redirect(url_for('owner.parkingspace'))
    try:
        for space in spot.spaces:
            db.session.delete(space)
        db.session.delete(spot)
        db.session.commit()
        flash("Parking spot deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting spot: " + str(e), "danger")
    return redirect(url_for('owner.parkingspace'))

@parking_bp.route('/booking_driver', methods=['GET'])
@login_required
def booking_driver():
    spot_id = request.args.get('spotId', type=int)
    if not spot_id:
        flash("No parking spot selected.", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    spot = ParkingSpot.query.get_or_404(spot_id)
    num2W = len([s for s in spot.spaces if s.vehicle_type == "2W"])
    num4W = len([s for s in spot.spaces if s.vehicle_type == "4W"])
    booked_intervals = {"2W": [], "4W": []}
    for space in spot.spaces:
        for booking in space.bookings:
            if booking.active:
                booked_intervals[space.vehicle_type].append({
                    "sub_spot": space.sub_spot_number - 1,
                    "start": booking.start_time.strftime("%H:%M"),
                    "end": booking.end_time.strftime("%H:%M")
                })
    return render_template(
        'booking_driver.html',
        spot=spot,
        num2W=num2W,
        num4W=num4W,
        booked_intervals=booked_intervals
    )

@parking_bp.route('/book/<int:spot_id>', methods=['POST'], endpoint='book_spot_driver')
@login_required
def book_spot(spot_id):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if session.get('role') != 'driver':
        msg = "Only drivers can book spots."
        if is_ajax:
            return jsonify({"error": msg}), 403
        flash(msg, "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    cart_data = request.form.get('cart_data')
    phone_number = request.form.get("phone_number")
    if not cart_data:
        msg = "No booking selections found."
        if is_ajax:
            return jsonify({"error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    if phone_number is None or phone_number.strip() == "":
        msg = "Phone number is required."
        if is_ajax:
            return jsonify({"error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    try:
        selections = json.loads(cart_data)
    except Exception as e:
        msg = "Invalid booking data."
        if is_ajax:
            return jsonify({"error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    errors = []
    session_id = str(uuid.uuid4())
    for selection in selections:
        vehicle_type = selection.get("vehicle_type")
        sub_spot = selection.get("sub_spot")
        booking_start = selection.get("booking_start")
        booking_end = selection.get("booking_end")
        sel_vehicle_number = selection.get("vehicle_number")
        if vehicle_type is None or booking_start is None or booking_end is None or sub_spot is None or (sel_vehicle_number is None or sel_vehicle_number.strip() == ""):
            errors.append("Missing booking information in one of your selections.")
            continue
        try:
            booking_start_time = datetime.strptime(booking_start, "%H:%M").time()
            booking_end_time = datetime.strptime(booking_end, "%H:%M").time()
        except ValueError:
            errors.append("Invalid time format in one of your selections. Use HH:MM.")
            continue
        if booking_end_time <= booking_start_time:
            errors.append("One selection has an end time not after its start time.")
            continue
        sub_spot_db = int(sub_spot) + 1
        space = ParkingSpace.query.filter_by(
            parking_spot_id=spot_id,
            vehicle_type=vehicle_type,
            sub_spot_number=sub_spot_db
        ).first()
        if not space:
            errors.append(f"Parking space not found for {vehicle_type} - Spot #{sub_spot_db}.")
            continue
        existing_bookings = Booking.query.filter_by(parking_space_id=space.id, active=True).all()
        conflict = any(
            booking_start_time < existing.end_time and booking_end_time > existing.start_time
            for existing in existing_bookings
        )
        if conflict:
            errors.append(f"Selection for {vehicle_type} - Spot #{sub_spot_db} overlaps with an existing booking.")
            continue
        new_booking = Booking(
            user_id=current_user.id,
            parking_space_id=space.id,
            start_time=booking_start_time,
            end_time=booking_end_time,
            active=True,
            vehicle_number=sel_vehicle_number.strip(),
            phone_number=phone_number.strip(),
            status="Pending",
            booked_vehicle_type=vehicle_type,
            session_id=session_id
        )
        db.session.add(new_booking)
    if errors:
        msg = " ".join(errors)
        if is_ajax:
            return jsonify({"error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        msg = "Error processing your booking: " + str(e)
        if is_ajax:
            return jsonify({"error": msg}), 500
        flash(msg, "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    spot = ParkingSpot.query.get_or_404(spot_id)
    booked_intervals = {"2W": [], "4W": []}
    for space in spot.spaces:
        for booking in space.bookings:
            if booking.active:
                booked_intervals[space.vehicle_type].append({
                    "sub_spot": space.sub_spot_number - 1,
                    "start": booking.start_time.strftime("%H:%M"),
                    "end": booking.end_time.strftime("%H:%M")
                })
    if is_ajax:
        return jsonify({"success": True, "booked_intervals": booked_intervals})
    flash("All selected spots booked successfully!", "success")
    return redirect(url_for('dashboard.driver_dashboard'))

@parking_bp.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        msg = "You cannot cancel a booking you did not make."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": msg}), 403
        flash(msg, "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    db.session.delete(booking)
    db.session.commit()
    msg = "Booking cancelled."
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})
    flash(msg, "success")
    return redirect(url_for('dashboard.driver_dashboard'))

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

@parking_bp.route('/available_slots/<int:spot_id>', methods=['GET'])
@login_required
def get_available_slots(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    available_from = spot.available_from or time(0, 0)
    available_to = spot.available_to or time(23, 0)

    def time_to_minutes(t):
        return t.hour * 60 + t.minute

    def minutes_to_time_str(m):
        hh = m // 60
        mm = m % 60
        return f"{hh:02d}:{mm:02d}"

    start_mins = time_to_minutes(available_from)
    end_mins = time_to_minutes(available_to)
    all_slots = []
    for m in range(start_mins, end_mins, 60):
        if m + 60 <= end_mins:
            all_slots.append(minutes_to_time_str(m))
    active_bookings = Booking.query.filter_by(active=True).all()
    blocked_ranges = []
    for booking in active_bookings:
        bs = time_to_minutes(booking.start_time)
        be = time_to_minutes(booking.end_time)
        blocked_ranges.append((bs, be))
    free_slots = []
    for slot in all_slots:
        slot_start = time_to_minutes(datetime.strptime(slot, "%H:%M").time())
        slot_end = slot_start + 60
        overlapped = False
        for bs, be in blocked_ranges:
            if slot_start < be and slot_end > bs:
                overlapped = True
                break
        if not overlapped:
            free_slots.append(slot)
    return jsonify(free_slots)
