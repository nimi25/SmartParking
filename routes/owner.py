import os, calendar
from types import SimpleNamespace
from datetime import datetime
from collections import defaultdict

from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from dateutil.relativedelta import relativedelta

from models import db, ParkingSpot, Booking, User, PaymentDetails

owner_bp = Blueprint('owner', __name__)

# ---------------- OWNER DASHBOARD ----------------
@owner_bp.route('/', methods=['GET'])
@login_required
def owner_dashboard():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
    joined_data = (
        db.session.query(Booking, User, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )

    all_bookings = []
    for b, u, s in joined_data:
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
                vehicle_type=b.booked_vehicle_type or "N/A",
                active=b.active,
                status=b.status
            )
        )

    total_bookings = len(all_bookings)
    total_revenue = sum(s.price for _, _, s in joined_data)
    active_spots = sum(1 for s in spots if s.availability)

    return render_template(
        'owner_dashboard.html',
        spots=spots,
        bookings=all_bookings,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        active_spots=active_spots
    )

# ---------------- GET ALL BOOKINGS ----------------
@owner_bp.route('/bookings', methods=['GET'])
@login_required
def bookings():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    joined_data = (
        db.session.query(Booking, User, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )

    all_bookings = []
    for b, u, s in joined_data:
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
                vehicle_type=b.booked_vehicle_type or "N/A",
                active=b.active,
                status=b.status
            )
        )

    return render_template('bookings.html', bookings=all_bookings)

# ---------------- OWNER’S PARKING SPACES ----------------
@owner_bp.route('/parkingspace', methods=['GET'])
@login_required
def parkingspace():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
    return render_template('parkingspace.html', spots=spots)

# ---------------- PAYMENT (CREATE/UPDATE) ----------------
@owner_bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    """
    Allows the owner to set/update their UPI ID, phone number,
    and upload a QR code image (stored in static/uploads).
    Uses PaymentDetails model, one row per owner_id.
    """
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    # 1) Get or create the PaymentDetails row for this owner
    payment_details = PaymentDetails.query.filter_by(owner_id=current_user.id).first()
    if not payment_details:
        payment_details = PaymentDetails(owner_id=current_user.id)
        db.session.add(payment_details)
        db.session.commit()

    if request.method == 'POST':
        upi_id = request.form.get('upi_id')
        phone_number = request.form.get('phone_number')
        qr_code_file = request.files.get('qr_code')

        # 2) Update fields if provided
        payment_details.upi_id = upi_id.strip() if upi_id else None
        payment_details.phone_number = phone_number.strip() if phone_number else None

        # 3) If a file was uploaded, save it
        if qr_code_file and qr_code_file.filename.strip():
            filename = secure_filename(qr_code_file.filename)
            save_path = os.path.join('static', 'uploads', filename)
            qr_code_file.save(save_path)
            payment_details.qr_code = filename

        db.session.commit()
        flash("Payment info updated successfully!", "success")
        return redirect(url_for('owner.payment'))

    # For GET requests, gather existing info from PaymentDetails
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

# ---------------- DELETE PAYMENT ----------------
@owner_bp.route('/delete_payment', methods=['POST'])
@login_required
def delete_payment():
    """
    Clears the current owner's UPI ID, phone number, and qr_code
    from PaymentDetails. Optionally remove the file from disk.
    """
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    payment_details = PaymentDetails.query.filter_by(owner_id=current_user.id).first()
    if payment_details:
        # Optionally remove QR file from disk
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

# ---------------- BOOKING METRICS ----------------
@owner_bp.route('/metrics', methods=['GET'])
@login_required
def metrics():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    # 1) Gather (Booking, User, ParkingSpot) for current_user's spots
    joined_data = (
        db.session.query(Booking, User, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )

    # Convert to list of Bookings for "this month" stats
    # We'll also handle naive vs. aware datetimes by forcibly removing tz
    def to_naive(dt):
        # If dt has tzinfo, remove it
        return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt

    all_bookings = []
    for b, u, s in joined_data:
        if b.created_at:
            # ensure it's naive
            b.created_at = to_naive(b.created_at)
            all_bookings.append((b, s))

    # 2) Define naive date range: from Feb 1, 2023 (no tz) to now (no tz)
    start_date = datetime(2025, 1, 1)
    end_date = to_naive(datetime.now())

    monthly_bookings_map = defaultdict(int)
    monthly_revenue_map = defaultdict(float)

    # Also track how many spots are currently available
    active_spots = ParkingSpot.query.filter_by(availability=True, owner_id=current_user.id).count()

    # 3) Filter bookings in the chosen range
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

    # 4) Build sorted lists for the monthly line/bar charts
    months_labels = []
    bookings_data = []
    revenue_data = []

    current_ptr = start_date
    while current_ptr <= end_date:
        y = current_ptr.year
        m = current_ptr.month
        month_label = calendar.month_abbr[m]  # e.g. "Feb", "Mar"
        months_labels.append(month_label)

        bcount = monthly_bookings_map.get((y, m), 0)
        rsum = monthly_revenue_map.get((y, m), 0.0)

        bookings_data.append(bcount)
        revenue_data.append(rsum)

        current_ptr += relativedelta(months=1)

    # 5) Real-time data for the current month
    this_month_year = end_date.year
    this_month_month = end_date.month

    # Bookings this month
    this_month_bookings = sum(
        1
        for (b, s) in all_bookings
        if b.created_at.year == this_month_year and b.created_at.month == this_month_month
    )

    # Revenue this month
    this_month_revenue = sum(
        s.price
        for (b, s) in all_bookings
        if b.created_at.year == this_month_year and b.created_at.month == this_month_month
    )

    # 6) Render the template
    return render_template(
        'metrics.html',
        # For the monthly overview card
        this_month_bookings=this_month_bookings,
        this_month_revenue=this_month_revenue,
        active_spots=active_spots,

        # For the line/bar charts
        months=months_labels,
        bookings_data=bookings_data,
        revenue_data=revenue_data
    )

# ---------------- BOOKING & PAYMENT HISTORY ----------------
@owner_bp.route('/history', methods=['GET'])
@login_required
def history():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    joined_data = (
        db.session.query(Booking, ParkingSpot)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )

    booking_history = [b for b, _ in joined_data]
    return render_template(
        'history_owner.html',
        booking_history=booking_history,
        payment_history=[]
    )

# ---------------- APPROVE BOOKING ----------------
@owner_bp.route('/approve_booking/<int:booking_id>', methods=['POST'])
@login_required
def approve_booking(booking_id):
    if session.get('role') != 'owner':
        flash("Unauthorized action!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    booking = Booking.query.get_or_404(booking_id)
    booking.status = "Approved"
    db.session.commit()
    flash("Booking approved!", "success")
    return redirect(url_for('owner.bookings'))
