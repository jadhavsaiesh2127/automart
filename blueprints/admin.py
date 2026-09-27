from functools import wraps
from datetime import datetime, timedelta
import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, current_app
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

from extensions import db
from models import Product, Order, OrderItem, User, VEHICLE_TYPES, PRODUCT_CATEGORIES, ORDER_STATUSES, BUSINESS_TYPES, gen_code

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


@bp.route("/")
@login_required
@admin_required
def dashboard():
    since = datetime.utcnow() - timedelta(days=30)
    orders_30d = Order.query.filter(Order.created_at >= since).all()

    revenue_30d = sum(o.total for o in orders_30d if o.status != "cancelled")
    b2b_revenue_30d = sum(o.total for o in orders_30d if o.status != "cancelled" and o.order_type == "b2b")
    b2c_revenue_30d = revenue_30d - b2b_revenue_30d
    pending_orders = Order.query.filter(Order.status.in_(["placed", "confirmed", "packed"])).count()
    total_products = Product.query.filter_by(is_active=True).count()
    low_stock = Product.query.filter(Product.stock <= 5, Product.is_active == True).order_by(Product.stock.asc()).limit(6).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    featured_parts = Product.query.filter_by(category="parts", is_active=True).order_by(Product.created_at.desc()).limit(6).all()
    pending_business_verification = User.query.filter_by(role="customer", account_type="business", business_verified=False).count()
    outstanding_credit = db.session.query(db.func.sum(User.credit_used)).filter(User.account_type == "business").scalar() or 0

    by_vehicle = {}
    for code, label in VEHICLE_TYPES:
        by_vehicle[label] = Product.query.filter_by(vehicle_type=code, is_active=True).count()

    return render_template(
        "admin/dashboard.html",
        revenue_30d=revenue_30d,
        b2b_revenue_30d=b2b_revenue_30d,
        b2c_revenue_30d=b2c_revenue_30d,
        order_count_30d=len(orders_30d),
        pending_orders=pending_orders,
        total_products=total_products,
        low_stock=low_stock,
        recent_orders=recent_orders,
        featured_parts=featured_parts,
        by_vehicle=by_vehicle,
        pending_business_verification=pending_business_verification,
        outstanding_credit=outstanding_credit,
    )


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@bp.route("/products")
@login_required
@admin_required
def products():
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=all_products)


@bp.route("/products/new", methods=["GET", "POST"])
@login_required
@admin_required
def product_new():
    if request.method == "POST":
        p = Product(sku=gen_code("SKU", 6))
        _apply_product_form(p, request.form)
        db.session.add(p)
        db.session.commit()
        flash(f"{p.name} added to catalog.", "success")
        return redirect(url_for("admin.products"))
    return render_template(
        "admin/product_form.html", product=None,
        vehicle_types=VEHICLE_TYPES, categories=PRODUCT_CATEGORIES,
    )


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def product_edit(product_id):
    p = Product.query.get_or_404(product_id)
    if request.method == "POST":
        _apply_product_form(p, request.form)
        db.session.commit()
        flash(f"{p.name} updated.", "success")
        return redirect(url_for("admin.products"))
    return render_template(
        "admin/product_form.html", product=p,
        vehicle_types=VEHICLE_TYPES, categories=PRODUCT_CATEGORIES,
    )


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
@admin_required
def product_delete(product_id):
    p = Product.query.get_or_404(product_id)
    p.is_active = False
    db.session.commit()
    flash(f"{p.name} removed from catalog.", "info")
    return redirect(url_for("admin.products"))


def _slugify(name):
    return "-".join(name.lower().split())[:200]


def _apply_product_form(p, form):
    from models import Product as ProductModel
    p.name = form.get("name", "").strip()
    base_slug = _slugify(p.name) or f"product-{p.sku}"
    slug = base_slug
    n = 1
    while ProductModel.query.filter(ProductModel.slug == slug, ProductModel.id != (p.id or -1)).first():
        n += 1
        slug = f"{base_slug}-{n}"
    p.slug = slug
    p.description = form.get("description", "").strip()
    p.brand = form.get("brand", "").strip()
    p.category = form.get("category")
    p.vehicle_type = form.get("vehicle_type")
    p.subcategory = form.get("subcategory", "").strip()
    p.price = int(form.get("price") or 0)
    p.mrp = int(form.get("mrp") or 0) or None
    p.bulk_price = int(form.get("bulk_price") or 0) or None
    p.bulk_min_qty = int(form.get("bulk_min_qty") or 0) or None
    p.stock = int(form.get("stock") or 0)
    p.weight_grams = int(form.get("weight_grams") or 500)
    p.image_url = form.get("image_url", "").strip() or p.image_url
    p.is_active = True



# ---------------------------------------------------------------------------
# Spare Parts Management
# ---------------------------------------------------------------------------

@bp.route("/parts")
@login_required
@admin_required
def parts():
    parts = Product.query.filter_by(category="parts").order_by(Product.created_at.desc()).all()
    return render_template("admin/parts.html", parts=parts)


@bp.route("/parts/new", methods=["GET", "POST"])
@login_required
@admin_required
def part_new():
    if request.method == "POST":
        p = Product(sku=gen_code("PART", 6))
        _apply_part_form(p, request.form, request.files.get("part_image"))
        db.session.add(p)
        db.session.commit()
        flash(f"{p.name} added to spare-parts catalog.", "success")
        return redirect(url_for("admin.parts"))
    return render_template(
        "admin/part_form.html",
        part=None,
        vehicle_types=VEHICLE_TYPES,
    )


@bp.route("/parts/<int:part_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def part_edit(part_id):
    p = Product.query.filter_by(id=part_id, category="parts").first_or_404()
    if request.method == "POST":
        _apply_part_form(p, request.form, request.files.get("part_image"))
        db.session.commit()
        flash(f"{p.name} updated.", "success")
        return redirect(url_for("admin.parts"))
    return render_template(
        "admin/part_form.html",
        part=p,
        vehicle_types=VEHICLE_TYPES,
    )


@bp.route("/parts/<int:part_id>/delete", methods=["POST"])
@login_required
@admin_required
def part_delete(part_id):
    p = Product.query.filter_by(id=part_id, category="parts").first_or_404()
    p.is_active = False
    db.session.commit()
    flash(f"{p.name} removed from the spare-parts catalog.", "info")
    return redirect(url_for("admin.parts"))


def _save_part_image(file_storage):
    """Save an uploaded spare-part image and return its static-relative URL."""
    if not file_storage or not file_storage.filename:
        return None

    allowed = current_app.config.get("ALLOWED_PART_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "webp"})
    original = secure_filename(file_storage.filename)
    if not original or "." not in original:
        abort(400, description="Please upload a valid image file.")

    extension = original.rsplit(".", 1)[1].lower()
    if extension not in allowed:
        abort(400, description="Allowed image types: PNG, JPG, JPEG, WEBP.")

    upload_dir = os.path.join(current_app.static_folder, "images", "parts", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"part-{uuid.uuid4().hex}.{extension}"
    file_storage.save(os.path.join(upload_dir, filename))
    return f"images/parts/uploads/{filename}"


def _apply_part_form(p, form, image_file=None):
    from models import Product as ProductModel

    p.name = form.get("name", "").strip()
    if not p.name:
        abort(400)

    base_slug = _slugify(p.name) or f"part-{p.sku}"
    slug = base_slug
    n = 1
    while ProductModel.query.filter(
        ProductModel.slug == slug,
        ProductModel.id != (p.id or -1)
    ).first():
        n += 1
        slug = f"{base_slug}-{n}"

    p.slug = slug
    p.description = form.get("description", "").strip()
    p.brand = form.get("brand", "").strip()
    p.category = "parts"
    p.vehicle_type = form.get("vehicle_type")
    p.subcategory = form.get("subcategory", "").strip()
    p.price = max(0, int(form.get("price") or 0))
    p.mrp = max(0, int(form.get("mrp") or 0)) or None
    p.bulk_price = max(0, int(form.get("bulk_price") or 0)) or None
    p.bulk_min_qty = max(0, int(form.get("bulk_min_qty") or 0)) or None
    p.stock = max(0, int(form.get("stock") or 0))
    p.weight_grams = max(1, int(form.get("weight_grams") or 500))
    uploaded_image = _save_part_image(image_file)
    if uploaded_image:
        p.image_url = uploaded_image
    else:
        image_url = form.get("image_url", "").strip()
        # Normalize local static URLs so the storefront can serve them
        # through Flask's static endpoint.
        if image_url.startswith("/static/"):
            image_url = image_url[len("/static/"):]
        p.image_url = image_url or p.image_url
    p.is_active = True

# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@bp.route("/orders")
@login_required
@admin_required
def orders():
    status_filter = request.args.get("status", "")
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_orders = query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=all_orders, statuses=ORDER_STATUSES, status_filter=status_filter)


@bp.route("/orders/<order_number>")
@login_required
@admin_required
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("admin/order_detail.html", order=order, statuses=ORDER_STATUSES)


@bp.route("/orders/<order_number>/status", methods=["POST"])
@login_required
@admin_required
def order_update_status(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    new_status = request.form.get("status")
    if new_status in ORDER_STATUSES:
        order.status = new_status
        db.session.commit()
        flash(f"Order {order.order_number} marked {order.status_label}.", "success")
    return redirect(url_for("admin.order_detail", order_number=order_number))


# ---------------------------------------------------------------------------
# Customers (read-only view)
# ---------------------------------------------------------------------------

@bp.route("/customers")
@login_required
@admin_required
def customers():
    filter_type = request.args.get("type", "")
    query = User.query.filter_by(role="customer")
    if filter_type in ("individual", "business"):
        query = query.filter_by(account_type=filter_type)
    all_customers = query.order_by(User.created_at.desc()).all()
    pending_verification = User.query.filter_by(role="customer", account_type="business", business_verified=False).count()
    return render_template("admin/customers.html", customers=all_customers, filter_type=filter_type, pending_verification=pending_verification)


@bp.route("/customers/<int:user_id>/verify", methods=["POST"])
@login_required
@admin_required
def customer_verify(user_id):
    user = User.query.get_or_404(user_id)
    if user.account_type != "business":
        abort(400)
    user.business_verified = True
    credit_limit = request.form.get("credit_limit", type=int)
    if credit_limit is not None:
        user.credit_limit = max(0, credit_limit)
    db.session.commit()
    flash(f"{user.company_name or user.name} verified with a ₹{user.credit_limit:,} credit limit.", "success")
    return redirect(url_for("admin.customers"))


@bp.route("/customers/<int:user_id>/revoke", methods=["POST"])
@login_required
@admin_required
def customer_revoke(user_id):
    user = User.query.get_or_404(user_id)
    user.business_verified = False
    user.credit_limit = 0
    db.session.commit()
    flash(f"Credit terms revoked for {user.company_name or user.name}.", "info")
    return redirect(url_for("admin.customers"))
