from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, BUSINESS_TYPES

bp = Blueprint("auth", __name__, url_prefix="/account")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard") if current_user.is_admin else url_for("storefront.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name.split()[0]}.", "success")
            next_url = request.args.get("next")
            if user.is_admin:
                return redirect(next_url or url_for("admin.dashboard"))
            return redirect(next_url or url_for("storefront.home"))

        flash("Incorrect email or password.", "error")

    return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("storefront.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        city = request.form.get("city", "").strip()
        account_type = request.form.get("account_type", "individual")
        if account_type not in ("individual", "business"):
            account_type = "individual"

        if not name or not email or not password:
            flash("Name, email, and password are required.", "error")
            return render_template("auth/register.html", business_types=BUSINESS_TYPES)

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("auth/register.html", business_types=BUSINESS_TYPES)

        user = User(name=name, email=email, phone=phone, city=city, role="customer", account_type=account_type)
        if account_type == "business":
            user.company_name = request.form.get("company_name", "").strip()
            user.gst_number = request.form.get("gst_number", "").strip().upper()
            user.business_type = request.form.get("business_type", "other")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        if account_type == "business":
            flash("Business account created. Bulk pricing is live now — an admin will review your account for Net 30 credit terms.", "success")
        else:
            flash("Account created. Welcome to AutoMart!", "success")
        return redirect(url_for("storefront.home"))

    return render_template("auth/register.html", business_types=BUSINESS_TYPES)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been signed out.", "info")
    return redirect(url_for("storefront.home"))
