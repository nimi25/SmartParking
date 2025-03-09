from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, bcrypt
import os

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/driver', methods=['GET', 'POST'])
@login_required
def driver_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        profile_pic = request.files.get('profile_pic')
        current_user.username = username
        current_user.email = email
        if password:
            current_user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        if profile_pic:
            filename = profile_pic.filename
            profile_pic.save(os.path.join('static/uploads', filename))
            current_user.profile_pic = filename
        db.session.commit()
        flash("Profile updated", "success")
        return redirect(url_for('profile.driver_profile'))
    return render_template('profile_driver.html')

@profile_bp.route('/owner', methods=['GET', 'POST'])
@login_required
def owner_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        profile_pic = request.files.get('profile_pic')
        current_user.username = username
        current_user.email = email
        if password:
            current_user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        if profile_pic:
            filename = profile_pic.filename
            profile_pic.save(os.path.join('static/uploads', filename))
            current_user.profile_pic = filename
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile.owner_profile'))
    return render_template('profile_owner.html')

@profile_bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        profile_pic = request.files.get('profile_pic')
        current_user.username = username
        current_user.email = email
        if password:
            current_user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        if profile_pic:
            filename = profile_pic.filename
            profile_pic.save(os.path.join('static/uploads', filename))
            current_user.profile_pic = filename
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile.admin_profile'))
    return render_template('profile_admin.html')
