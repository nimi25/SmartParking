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
