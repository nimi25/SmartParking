import os
from types import SimpleNamespace
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, ParkingSpot, Booking, User

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
    """
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    if request.method == 'POST':
        upi_id = request.form.get('upi_id')
        phone_number = request.form.get('phone_number')
        qr_code_file = request.files.get('qr_code')

        # Update fields if provided
        if upi_id is not None:
            current_user.upi_id = upi_id
        if phone_number is not None:
            current_user.phone_number = phone_number

        # If a file was uploaded, save it
        if qr_code_file and qr_code_file.filename.strip():
            filename = secure_filename(qr_code_file.filename)
            save_path = os.path.join('static', 'uploads', filename)
            qr_code_file.save(save_path)
            current_user.qr_code = filename

        db.session.commit()
        flash("Payment info updated successfully!", "success")
        return redirect(url_for('owner.payment'))

    # For GET requests, gather existing info from current_user
    payment_info = {
        "upi_id": getattr(current_user, "upi_id", ""),
        "phone_number": getattr(current_user, "phone_number", ""),
        "qr_code": getattr(current_user, "qr_code", None)
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
    Clears the current owner's UPI ID, phone number, and qr_code.
    This way, the user can effectively 'delete' their payment info.
    """
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    current_user.upi_id = None
    current_user.phone_number = None

    # Optionally delete the file from disk if you want to truly remove it:
    if current_user.qr_code:
        try:
            file_path = os.path.join('static', 'uploads', current_user.qr_code)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print("Error removing old QR code file:", e)

    current_user.qr_code = None
    db.session.commit()

    flash("Payment details deleted successfully!", "success")
    return redirect(url_for('owner.payment'))

# ---------------- BOOKING METRICS ----------------
@owner_bp.route('/metrics', methods=['GET'])
@login_required
def metrics():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
    joined_data = (
        db.session.query(Booking, ParkingSpot)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )

    total_bookings = len(joined_data)
    total_revenue = sum(s.price for _, s in joined_data)
    active_spots = sum(1 for s in spots if s.availability)

    return render_template(
        'metrics.html',
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        active_spots=active_spots,
        avg_daily_bookings=0,
        peak_usage_time="N/A",
        monthly_growth=0
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

# ---------------- OWNER PROFILE MANAGEMENT ----------------
@owner_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def owner_profile():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        profile_pic = request.files.get('profile_pic')

        if username:
            current_user.username = username
        if email:
            current_user.email = email
        if password:
            from models import bcrypt
            current_user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        if profile_pic and profile_pic.filename.strip():
            filename = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join('static', 'uploads', filename))
            current_user.profile_pic = filename

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('owner.owner_profile'))

    return render_template('profile_owner.html')

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
