from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from datetime import datetime, timedelta

from extensions import db
from models import Product, CartItem, Order, OrderItem, Payment, VEHICLE_TYPES, PRODUCT_CATEGORIES
from blueprints.payments_gateway import process_payment, get_emi_options

bp = Blueprint("storefront", __name__)


# ---------------------------------------------------------------------------
# Browsing
# ---------------------------------------------------------------------------

@bp.route("/")
def home():
    featured = Product.query.filter_by(is_active=True).order_by(Product.rating.desc()).limit(8).all()
    express_picks = (
        Product.query.filter(Product.is_active == True, Product.weight_grams <= 5000, Product.stock > 0)
        .order_by(Product.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "storefront/home.html",
        featured=featured,
        express_picks=express_picks,
        vehicle_types=VEHICLE_TYPES,
        categories=PRODUCT_CATEGORIES,
    )


@bp.route("/shop")
def shop():
    vehicle_type = request.args.get("vehicle_type", "")
    category = request.args.get("category", "")
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "popular")

    query = Product.query.filter_by(is_active=True)
    if vehicle_type:
        query = query.filter_by(vehicle_type=vehicle_type)
    if category:
        query = query.filter_by(category=category)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.ilike(like), Product.brand.ilike(like), Product.subcategory.ilike(like)))

    if sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.rating.desc())

    products = query.all()

    return render_template(
        "storefront/shop.html",
        products=products,
        vehicle_types=VEHICLE_TYPES,
        categories=PRODUCT_CATEGORIES,
        selected_vehicle=vehicle_type,
        selected_category=category,
        q=q,
        sort=sort,
    )


@bp.route("/product/<slug>")
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    related = (
        Product.query.filter(
            Product.vehicle_type == product.vehicle_type,
            Product.id != product.id,
            Product.is_active == True,
        )
        .limit(4)
        .all()
    )
    return render_template("storefront/product.html", product=product, related=related)


# ---------------------------------------------------------------------------
# Cart (persisted per logged-in user)
# ---------------------------------------------------------------------------

def _cart_query():
    return CartItem.query.filter_by(user_id=current_user.id)


@bp.route("/cart")
@login_required
def cart():
    items = _cart_query().all()
    subtotal = sum(i.line_total_for(current_user.account_type) for i in items)
    all_express = bool(items) and all(i.product.is_express_eligible for i in items)
    return render_template("storefront/cart.html", items=items, subtotal=subtotal, all_express=all_express)


@bp.route("/cart/add", methods=["POST"])
@login_required
def cart_add():
    product_id = request.form.get("product_id", type=int)
    qty = max(1, request.form.get("quantity", 1, type=int))
    product = Product.query.get_or_404(product_id)

    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if item:
        item.quantity += qty
    else:
        item = CartItem(user_id=current_user.id, product_id=product.id, quantity=qty)
        db.session.add(item)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        count = sum(i.quantity for i in _cart_query().all())
        return jsonify({"ok": True, "cart_count": count, "message": f"Added {product.name} to cart"})

    flash(f"Added {product.name} to your cart.", "success")
    return redirect(request.referrer or url_for("storefront.shop"))


@bp.route("/cart/update", methods=["POST"])
@login_required
def cart_update():
    item_id = request.form.get("item_id", type=int)
    qty = request.form.get("quantity", type=int)
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    if qty and qty > 0:
        item.quantity = qty
        db.session.commit()
    else:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("storefront.cart"))


@bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def cart_remove(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Item removed from cart.", "info")
    return redirect(url_for("storefront.cart"))


# ---------------------------------------------------------------------------
# Checkout -> Payment -> Confirmation
# ---------------------------------------------------------------------------

@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items = _cart_query().all()
    if not items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("storefront.shop"))

    all_express = all(i.product.is_express_eligible for i in items)
    subtotal = sum(i.line_total_for(current_user.account_type) for i in items)

    if request.method == "POST":
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        delivery_type = request.form.get("delivery_type", "standard")

        if not address or not city or not pincode:
            flash("Please fill in your full delivery address.", "error")
            return render_template("storefront/checkout.html", items=items, subtotal=subtotal, all_express=all_express)

        session["checkout"] = {
            "address": f"{address}, {city}, {state} {pincode}".strip(", "),
            "delivery_type": delivery_type if all_express else "standard",
            "po_number": request.form.get("po_number", "").strip(),
        }
        return redirect(url_for("storefront.payment"))

    return render_template(
        "storefront/checkout.html",
        items=items,
        subtotal=subtotal,
        all_express=all_express,
        user=current_user,
    )


def _delivery_fee(delivery_type, subtotal):
    cfg = current_app.config
    if subtotal >= cfg.get("FREE_DELIVERY_THRESHOLD", 999):
        return 0
    return cfg.get("EXPRESS_DELIVERY_FEE", 49) if delivery_type == "express" else cfg.get("STANDARD_DELIVERY_FEE", 0)


@bp.route("/checkout/payment", methods=["GET", "POST"])
@login_required
def payment():
    checkout_info = session.get("checkout")
    items = _cart_query().all()
    if not checkout_info or not items:
        flash("Please complete your delivery details first.", "info")
        return redirect(url_for("storefront.checkout"))

    subtotal = sum(i.line_total_for(current_user.account_type) for i in items)
    delivery_fee = _delivery_fee(checkout_info["delivery_type"], subtotal)
    total = subtotal + delivery_fee
    emi_options = get_emi_options(total) if total >= current_app.config.get("EMI_MIN_ORDER_VALUE", 1500) else []

    credit_eligible = (
        current_user.is_business
        and current_user.business_verified
        and current_user.credit_available >= total
    )

    if request.method == "POST":
        method = request.form.get("method")
        instrument_label = None

        if method == "credit_terms" and not credit_eligible:
            flash("Business credit isn't available for this order. Choose another payment method.", "error")
            return redirect(url_for("storefront.payment"))

        if method == "upi":
            vpa = request.form.get("upi_id", "").strip()
            instrument_label = f"UPI: {vpa}" if vpa else "UPI"
        elif method in ("card", "credit_card"):
            card_number = request.form.get("card_number", "").strip()
            last4 = card_number[-4:] if len(card_number) >= 4 else "0000"
            label = "Credit card" if method == "credit_card" else "Debit card"
            instrument_label = f"{label} ending {last4}"
        elif method == "emi":
            instrument_label = "EMI"
        elif method == "cod":
            instrument_label = "Cash on Delivery"
        elif method == "credit_terms":
            instrument_label = f"Business Credit — {current_user.company_name or current_user.name}"

        emi_tenure = request.form.get("emi_tenure", type=int)
        result = process_payment(method, total, instrument_label, emi_tenure)

        order = Order(
            user_id=current_user.id,
            order_type="b2b" if current_user.is_business else "b2c",
            status="placed",
            delivery_type=checkout_info["delivery_type"],
            delivery_address=checkout_info["address"],
            po_number=checkout_info.get("po_number") or None,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            discount=0,
            total=total,
            is_credit_order=(method == "credit_terms"),
            credit_due_date=(datetime.utcnow() + timedelta(days=30)) if method == "credit_terms" else None,
        )
        db.session.add(order)
        db.session.flush()  # get order.id before adding items

        for ci in items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=ci.product_id,
                product_name=ci.product.name,
                quantity=ci.quantity,
                unit_price=ci.unit_price(current_user.account_type),
            ))
            if result["success"]:
                ci.product.stock = max(0, ci.product.stock - ci.quantity)

        pay = Payment(
            order_id=order.id,
            method=method,
            status=result["status"],
            transaction_id=result["transaction_id"],
            instrument_label=instrument_label,
        )
        if method == "emi" and emi_tenure:
            monthly, total_payable = None, None
            for opt in emi_options:
                if opt["tenure"] == emi_tenure:
                    monthly, total_payable = opt["monthly"], opt["total"]
            pay.emi_tenure_months = emi_tenure
            pay.emi_monthly_amount = monthly
            pay.emi_total_payable = total_payable
        db.session.add(pay)

        if not result["success"]:
            db.session.rollback()
            flash(result["message"], "error")
            return render_template(
                "storefront/payment.html",
                items=items, subtotal=subtotal, delivery_fee=delivery_fee, total=total,
                emi_options=emi_options, checkout_info=checkout_info, credit_eligible=credit_eligible,
            )

        if method == "credit_terms":
            current_user.credit_used += total

        for ci in items:
            db.session.delete(ci)
        db.session.commit()
        session.pop("checkout", None)

        flash(result["message"], "success")
        return redirect(url_for("storefront.order_confirmation", order_number=order.order_number))

    return render_template(
        "storefront/payment.html",
        items=items, subtotal=subtotal, delivery_fee=delivery_fee, total=total,
        emi_options=emi_options, checkout_info=checkout_info, credit_eligible=credit_eligible,
    )


@bp.route("/order/<order_number>/confirmation")
@login_required
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    return render_template("storefront/order_success.html", order=order)


@bp.route("/account/orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("storefront/my_orders.html", orders=orders)


@bp.route("/account/orders/<order_number>")
@login_required
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    return render_template("storefront/order_detail.html", order=order)


CANCELLABLE_STATUSES = ("placed", "confirmed")


@bp.route("/account/orders/<order_number>/cancel", methods=["POST"])
@login_required
def order_cancel(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()

    if order.status not in CANCELLABLE_STATUSES:
        flash("This order can no longer be cancelled — it's already being processed.", "error")
        return redirect(url_for("storefront.order_detail", order_number=order.order_number))

    # Restock items
    for item in order.items:
        if item.product:
            item.product.stock += item.quantity

    # Release any Net-30 credit that was reserved for this order
    if order.is_credit_order and not order.credit_settled:
        current_user.credit_used = max(0, current_user.credit_used - order.total)

    order.status = "cancelled"
    db.session.commit()

    flash(f"Order {order.order_number} has been cancelled.", "info")
    return redirect(url_for("storefront.order_detail", order_number=order.order_number))
