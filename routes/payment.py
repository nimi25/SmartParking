from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, PaymentDetails as Payment, Booking

payment_bp = Blueprint('payment', __name__)

# -------------------- PROCESS PAYMENT ROUTE --------------------
@payment_bp.route('/process', methods=['GET', 'POST'])
@login_required
def process_payment():
    if request.method == 'GET':
        booking_id = request.args.get('booking_id')

        if not booking_id:
            flash("Invalid booking.", "danger")
            return redirect(url_for('dashboard.dashboard'))

        booking = Booking.query.get(booking_id)
        if not booking or booking.user_id != current_user.id:
            flash("Unauthorized booking access.", "danger")
            return redirect(url_for('dashboard.dashboard'))

        # Render your payment form/page
        return render_template('payment.html', booking_id=booking_id, amount=booking.spot.price)

    # If POST => store or update payment info
    booking_id = request.form.get('booking_id')
    upi_id = request.form.get('upi_id')
    phone_number = request.form.get('phone_number')
    payment_method = request.form.get('payment_method')  # e.g. "UPI", "QR Code"

    if not (upi_id or phone_number):
        flash("Please provide valid payment details.", "danger")
        return redirect(url_for('payment.process_payment', booking_id=booking_id))

    # Create the payment record in DB
    payment = Payment(
        user_id=current_user.id,
        booking_id=booking_id,
        upi_id=upi_id,
        phone_number=phone_number,
        payment_method=payment_method,
        status="Pending"
    )
    db.session.add(payment)
    db.session.commit()

    flash("Payment details submitted successfully!", "success")
    return redirect(url_for('dashboard.my_bookings'))

# -------------------- DELETE PAYMENT ROUTE --------------------
@payment_bp.route('/delete_payment', methods=['POST'])
@login_required
def delete_payment():
    """
    This route is called when user clicks "Delete" button on payment.html.
    We find the payment record by ID, ensure it belongs to current_user,
    and then remove it from the DB.
    """
    payment_id = request.form.get('payment_id')
    if not payment_id:
        flash("No payment specified to delete.", "danger")
        return redirect(url_for('payment.process_payment'))

    # Only allow deleting if the payment belongs to the logged-in user
    payment_info = Payment.query.filter_by(id=payment_id, user_id=current_user.id).first()
    if not payment_info:
        flash("Payment details not found or unauthorized.", "danger")
        return redirect(url_for('payment.process_payment'))

    db.session.delete(payment_info)
    db.session.commit()

    flash("Payment details deleted successfully!", "success")
    return redirect(url_for('payment.process_payment'))

# -------------------- DISPLAY PAYMENT DETAILS (optional) --------------------
@payment_bp.route('/payment_details/<int:booking_id>')
@login_required
def payment_details(booking_id):
    payment = Payment.query.filter_by(booking_id=booking_id, user_id=current_user.id).first()
    if not payment:
        flash("No payment details found.", "warning")
        return redirect(url_for('dashboard.my_bookings'))
    return render_template('payment_details.html', payment=payment)
