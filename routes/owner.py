import os, calendar
from types import SimpleNamespace
from datetime import datetime
from collections import defaultdict
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import joinedload
from models import db, ParkingSpot, Booking, User, PaymentDetails, ParkingSpace

owner_bp = Blueprint('owner', __name__)

# Custom filter to convert ParkingSpace objects to dicts for JSON serialization.
@owner_bp.app_template_filter('space_to_dict')
def space_to_dict(space):
    return {
        'id': space.id,
        'vehicle_type': space.vehicle_type,
        'sub_spot': space.sub_spot_number,
        'has_booking': True if space.bookings and len(space.bookings) > 0 else False
    }

@owner_bp.route('/', methods=['GET'])
@login_required
def owner_dashboard():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))
    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).options(joinedload(ParkingSpot.spaces)).all()
    joined_data = (
        db.session.query(Booking, User, ParkingSpace, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpace, Booking.parking_space_id == ParkingSpace.id)
        .join(ParkingSpot, ParkingSpace.parking_spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )
    all_bookings = []
    for b, u, ps, s in joined_data:
        all_bookings.append(
            SimpleNamespace(
                id=b.id,
                driver_name=u.username,
                email=u.email,
                vehicle_number=b.vehicle_number,
                spot_location=s.location,
                spot_price=s.price,
                spot_lat=s.lat,
                spot_lng=s.lng,
                created_at=b.created_at,
                start_time=b.start_time,
                end_time=b.end_time,
                vehicle_type=ps.vehicle_type,
                sub_spot_number=ps.sub_spot_number,
                active=b.active,
                status=b.status,
                is_approved=b.is_approved,
                session_id=b.session_id if b.session_id is not None else str(b.id),
                phone_number=b.phone_number
            )
        )
    total_bookings = len(all_bookings)
    total_revenue = sum(s.price for (_, _, _, s) in joined_data)
    active_spots = sum(1 for s in spots if s.availability)
    return render_template('owner_dashboard.html',
                           spots=spots,
                           bookings=all_bookings,
                           total_bookings=total_bookings,
                           total_revenue=total_revenue,
                           active_spots=active_spots)

@owner_bp.route('/bookings', methods=['GET'])
@login_required
def bookings():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))

    joined_data = (
        db.session.query(Booking, User, ParkingSpace, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpace, Booking.parking_space_id == ParkingSpace.id)
        .join(ParkingSpot, ParkingSpace.parking_spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id,
                Booking.status.in_(["Pending", "Approved", "Rejected"]))
        .all()
    )
    all_bookings = []
    for b, u, ps, s in joined_data:
        # Compute the booking ID string exactly as in my_bookings.html
        booking_id_str = "BK" + b.created_at.strftime('%d%H%M%S')
        if b.vehicle_number:
            booking_id_str += b.vehicle_number[-2:]
        else:
            booking_id_str += str(b.id)
        all_bookings.append(
            SimpleNamespace(
                id=b.id,
                booking_id=booking_id_str,
                driver_name=u.username,
                email=u.email,
                vehicle_number=b.vehicle_number,
                spot_location=s.location,
                spot_price=s.price,
                spot_lat=s.lat,
                spot_lng=s.lng,
                created_at=b.created_at,
                start_time=b.start_time,
                end_time=b.end_time,
                vehicle_type=ps.vehicle_type,
                sub_spot_number=ps.sub_spot_number,
                active=b.active,
                status=b.status,
                is_approved=b.is_approved,
                session_id=b.session_id if b.session_id is not None else str(b.id),
                phone_number=b.phone_number
            )
        )
    grouped_bookings = defaultdict(list)
    for booking in all_bookings:
        grouped_bookings[booking.session_id].append(booking)
    return render_template("bookings.html", grouped_bookings=dict(grouped_bookings))

@owner_bp.route('/parkingspace', methods=['GET'])
@login_required
def parkingspace():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))
    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).options(joinedload(ParkingSpot.spaces)).all()
    return render_template('parkingspace.html', spots=spots)

@owner_bp.route('/manage_spaces/<int:spot_id>', methods=['GET'])
@login_required
def manage_spaces(spot_id):
    spot = ParkingSpot.query.filter_by(id=spot_id, owner_id=current_user.id).first_or_404()
    spaces = sorted(spot.spaces, key=lambda s: (s.vehicle_type, s.sub_spot_number))
    return render_template('manage_spaces.html', spot=spot, spaces=spaces)

@owner_bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))

    payment_details = PaymentDetails.query.filter_by(owner_id=current_user.id).first()
    if not payment_details:
        payment_details = PaymentDetails(owner_id=current_user.id)
        db.session.add(payment_details)
        db.session.commit()

    if request.method == 'POST':
        upi_id = request.form.get('upi_id')
        phone_number = request.form.get('phone_number')
        qr_code_file = request.files.get('qr_code')

        payment_details.upi_id = upi_id.strip() if upi_id else None
        payment_details.phone_number = phone_number.strip() if phone_number else None

        if qr_code_file and qr_code_file.filename.strip():
            filename = secure_filename(qr_code_file.filename)
            save_path = os.path.join('static', 'uploads', filename)
            qr_code_file.save(save_path)
            payment_details.qr_code = filename

        db.session.commit()
        flash("Payment info updated successfully!", "success")
        return redirect(url_for('owner.payment'))

    payment_info = {
        "upi_id": payment_details.upi_id,
        "phone_number": payment_details.phone_number,
        "qr_code": payment_details.qr_code
    }

    return render_template(
        'payment.html',
        payment_info=payment_info,
        last_payment=500,
        last_payment_date="2025-03-04",
        total_paid=2500,
        pending_invoices=1,
        pending_amount=300,
        refunds=0
    )

@owner_bp.route('/delete_payment', methods=['POST'])
@login_required
def delete_payment():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))

    payment_details = PaymentDetails.query.filter_by(owner_id=current_user.id).first()
    if payment_details:
        if payment_details.qr_code:
            try:
                file_path = os.path.join('static', 'uploads', payment_details.qr_code)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print("Error removing old QR code file:", e)

        payment_details.upi_id = None
        payment_details.phone_number = None
        payment_details.qr_code = None
        db.session.commit()
        flash("Payment details deleted successfully!", "success")
    else:
        flash("No payment info to delete.", "warning")

    return redirect(url_for('owner.payment'))

@owner_bp.route('/metrics', methods=['GET'])
@login_required
def metrics():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))

    joined_data = (
        db.session.query(Booking, User, ParkingSpace, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpace, Booking.parking_space_id == ParkingSpace.id)
        .join(ParkingSpot, ParkingSpace.parking_spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )

    def to_naive(dt):
        return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt

    all_bookings = []
    for b, u, ps, s in joined_data:
        if b.created_at:
            b.created_at = to_naive(b.created_at)
            all_bookings.append((b, s))

    start_date = datetime(2025, 1, 1)
    end_date = to_naive(datetime.now())

    from collections import defaultdict
    monthly_bookings_map = defaultdict(int)
    monthly_revenue_map = defaultdict(float)

    active_spots = ParkingSpot.query.filter_by(availability=True, owner_id=current_user.id).count()

    bookings_in_range = [
        (b, s) for (b, s) in all_bookings
        if b.created_at >= start_date and b.created_at <= end_date
    ]

    for (b, s) in bookings_in_range:
        y = b.created_at.year
        m = b.created_at.month
        monthly_bookings_map[(y, m)] += 1
        if s:
            monthly_revenue_map[(y, m)] += s.price

    months_labels = []
    bookings_data = []
    revenue_data = []

    current_ptr = start_date
    while current_ptr <= end_date:
        y = current_ptr.year
        m = current_ptr.month
        month_label = calendar.month_abbr[m]
        months_labels.append(month_label)
        bcount = monthly_bookings_map.get((y, m), 0)
        rsum = monthly_revenue_map.get((y, m), 0.0)
        bookings_data.append(bcount)
        revenue_data.append(rsum)
        current_ptr += relativedelta(months=1)

    this_month_year = end_date.year
    this_month_month = end_date.month

    this_month_bookings = sum(
        1
        for (b, s) in all_bookings
        if b.created_at.year == this_month_year and b.created_at.month == this_month_month
    )

    this_month_revenue = sum(
        s.price
        for (b, s) in all_bookings
        if b.created_at.year == this_month_year and b.created_at.month == this_month_month
    )

    return render_template(
        'metrics.html',
        this_month_bookings=this_month_bookings,
        this_month_revenue=this_month_revenue,
        active_spots=active_spots,
        months=months_labels,
        bookings_data=bookings_data,
        revenue_data=revenue_data
    )

@owner_bp.route('/history', methods=['GET'])
@login_required
def history():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.dashboard'))

    joined_data = (
        db.session.query(Booking, ParkingSpot)
        .join(ParkingSpace, Booking.parking_space_id == ParkingSpace.id)
        .join(ParkingSpot, ParkingSpace.parking_spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )
    booking_history = [b for b, _ in joined_data]
    return render_template(
        'history_owner.html',
        booking_history=booking_history,
        payment_history=[]
    )

@owner_bp.route('/approve_booking/<int:booking_id>', methods=['POST'])
@login_required
def approve_booking(booking_id):
    if session.get('role') != 'owner':
        flash("Unauthorized action!", "danger")
        return redirect(url_for('dashboard.dashboard'))

    booking = Booking.query.get_or_404(booking_id)
    session_id = booking.session_id if booking.session_id else str(booking.id)
    bookings_in_session = Booking.query.filter_by(session_id=session_id).all()
    for b in bookings_in_session:
        b.status = "Approved"
        b.is_approved = True
    db.session.commit()
    flash("Booking(s) approved!", "success")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"success": True}
    return redirect(url_for('owner.bookings'))


@owner_bp.route('/reject_booking/<int:booking_id>', methods=['POST'])
@login_required
def reject_booking(booking_id):
    if session.get('role') != 'owner':
        flash("Unauthorized action!", "danger")
        return redirect(url_for('dashboard.dashboard'))

    booking = Booking.query.get_or_404(booking_id)
    session_id = booking.session_id if booking.session_id else str(booking.id)
    bookings_in_session = Booking.query.filter_by(session_id=session_id).all()

    for b in bookings_in_session:
        b.status = "Rejected"
        b.active = False
        b.is_approved = False
        # Optionally, free the parking space by marking it available.
        space = ParkingSpace.query.get(b.parking_space_id)
        if space:
            space.status = "available"

    db.session.commit()
    flash("Booking(s) rejected!", "success")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"success": True}
    return redirect(url_for('owner.bookings'))

@owner_bp.route('/edit_parking_spot/<int:spot_id>', methods=['POST'])
@login_required
def edit_parking_spot(spot_id):
    # Retrieve the parking spot belonging to the current owner.
    spot = ParkingSpot.query.filter_by(id=spot_id, owner_id=current_user.id).first_or_404()
    location = request.form.get('location')
    price = request.form.get('price')
    description = request.form.get('description')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    spaces_data = request.form.get('spaces_data')

    if not location or not price or not lat or not lng:
        flash("Missing required fields.", "danger")
        return redirect(url_for('owner.parkingspace'))

    try:
        price = float(price)
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        flash("Invalid numeric values.", "danger")
        return redirect(url_for('owner.parkingspace'))

    spot.location = location
    spot.price = price
    spot.description = description
    spot.lat = lat
    spot.lng = lng

    if spaces_data:
        import json
        try:
            new_spaces = json.loads(spaces_data)
        except Exception as e:
            flash("Error processing spaces data.", "danger")
            return redirect(url_for('owner.parkingspace'))

        # Get existing spaces sorted by sub_spot_number.
        existing_spaces = sorted(spot.spaces, key=lambda s: s.sub_spot_number)
        new_count = len(new_spaces)
        existing_count = len(existing_spaces)
        min_count = min(new_count, existing_count)

        # Update the common spaces.
        for i in range(min_count):
            # Update vehicle type.
            existing_spaces[i].vehicle_type = new_spaces[i].get('vehicle_type', existing_spaces[i].vehicle_type)
            # Use indexing to fetch 'sub_spot'; if missing, fallback to i+1.
            try:
                existing_spaces[i].sub_spot_number = int(new_spaces[i]['sub_spot'])
            except (KeyError, ValueError, TypeError):
                existing_spaces[i].sub_spot_number = i + 1

        # If more new spaces than existing, add the extras.
        if new_count > existing_count:
            for i in range(existing_count, new_count):
                try:
                    sub_spot = int(new_spaces[i]['sub_spot'])
                except (KeyError, ValueError, TypeError):
                    sub_spot = i + 1
                new_space = ParkingSpace(
                    parking_spot_id=spot.id,
                    vehicle_type=new_spaces[i].get('vehicle_type'),
                    sub_spot_number=sub_spot
                )
                db.session.add(new_space)

        # If fewer new spaces than existing, remove the extras only if they have no bookings.
        if existing_count > new_count:
            for space in existing_spaces[new_count:]:
                if space.bookings:
                    flash("Cannot remove a parking space that has existing bookings.", "danger")
                    return redirect(url_for('owner.parkingspace'))
                else:
                    db.session.delete(space)

    db.session.commit()
    flash("Parking spot updated successfully.", "success")
    return redirect(url_for('owner.parkingspace'))
