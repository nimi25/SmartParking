from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import razorpay
import os

payment_bp = Blueprint('payment', __name__)

# Configure your Razorpay credentials
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'your_test_key')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'your_test_secret')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@payment_bp.route('/process', methods=['GET', 'POST'])
@login_required
def process_payment():
    if request.method == 'GET':
        booking_id = request.args.get('booking_id')
        amount_str = request.args.get('amount')

        if not booking_id or not amount_str:
            flash("Invalid booking or amount.", "danger")
            return redirect(url_for('dashboard.dashboard'))

        return render_template('payment.html',
                               booking_id=booking_id,
                               amount=amount_str)

    booking_id = request.form.get('booking_id')
    payment_option = request.form.get('payment_option')  # e.g. UPI, card, netbanking
    amount_str = request.form.get('amount')

    try:
        amount = int(float(amount_str) * 100)
    except (ValueError, TypeError):
        flash("Invalid amount provided.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    try:
        razorpay_order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": "1"
        })
    except Exception as e:
        flash("Error creating payment order: " + str(e), "danger")
        return redirect(url_for('dashboard.dashboard'))

    order_id = razorpay_order['id']

    return render_template('razorpay_checkout.html',
                           order_id=order_id,
                           amount=amount,
                           booking_id=booking_id,
                           key_id=RAZORPAY_KEY_ID)

@payment_bp.route('/success')
@login_required
def payment_success():
    payment_id = request.args.get('payment_id')
    order_id = request.args.get('order_id')
    signature = request.args.get('signature')
    flash("Payment successful!", "success")
    return redirect(url_for('dashboard.dashboard'))
