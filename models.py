import random
import string
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

VEHICLE_TYPES = [
    ("car", "Cars"),
    ("bike", "Motorcycles"),
    ("scooter", "Scooters"),
    ("ev", "EV Vehicles"),
    ("auto_rickshaw", "Auto-Rickshaw"),
    ("tempo", "Tempo"),
    ("truck", "Small Trucks"),
]

PRODUCT_CATEGORIES = [
    ("parts", "Spare Parts"),
    ("accessories", "Accessories"),
]

ORDER_STATUSES = [
    "placed",
    "confirmed",
    "packed",
    "out_for_delivery",
    "delivered",
    "cancelled",
]

PAYMENT_METHODS = [
    ("upi", "UPI"),
    ("card", "Debit Card"),
    ("credit_card", "Credit Card"),
    ("emi", "EMI"),
    ("cod", "Cash on Delivery"),
    ("credit_terms", "Business Credit (Net 30)"),
]


def gen_code(prefix, length=8):
    chars = string.ascii_uppercase + string.digits
    return f"{prefix}-{''.join(random.choices(chars, k=length))}"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="customer")  # customer | admin

    # B2C vs B2B
    account_type = db.Column(db.String(20), default="individual")  # individual | business
    company_name = db.Column(db.String(160))
    gst_number = db.Column(db.String(20))
    business_type = db.Column(db.String(40))  # garage | retailer | fleet_operator | distributor | other
    business_verified = db.Column(db.Boolean, default=False)   # admin approves before credit terms unlock
    credit_limit = db.Column(db.Integer, default=0)             # outstanding Net-30 credit allowed, in INR
    credit_used = db.Column(db.Integer, default=0)

    address_line = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="customer", lazy="dynamic")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_business(self):
        return self.account_type == "business"

    @property
    def credit_available(self):
        return max(0, self.credit_limit - self.credit_used)

    @property
    def full_address(self):
        parts = [self.address_line, self.city, self.state, self.pincode]
        return ", ".join([p for p in parts if p])


BUSINESS_TYPES = [
    ("garage", "Garage / Workshop"),
    ("retailer", "Retail Shop"),
    ("fleet_operator", "Fleet Operator"),
    ("distributor", "Distributor / Wholesaler"),
    ("other", "Other Business"),
]


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    brand = db.Column(db.String(80))

    category = db.Column(db.String(20), nullable=False)     # parts | accessories
    vehicle_type = db.Column(db.String(20), nullable=False, index=True)  # see VEHICLE_TYPES
    subcategory = db.Column(db.String(80))  # e.g. "Brakes", "Filters", "Lighting"

    price = db.Column(db.Integer, nullable=False)      # in INR, integer paise-free for simplicity
    mrp = db.Column(db.Integer)                          # strike-through price
    stock = db.Column(db.Integer, default=0)

    # B2B tiered pricing — when set, business accounts ordering >= bulk_min_qty
    # of this item pay bulk_price per unit instead of the retail price.
    bulk_price = db.Column(db.Integer)
    bulk_min_qty = db.Column(db.Integer)

    weight_grams = db.Column(db.Integer, default=500)
    image_url = db.Column(db.String(300))
    rating = db.Column(db.Float, default=4.3)
    rating_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", backref="product", lazy="dynamic")

    @property
    def is_express_eligible(self):
        from flask import current_app
        limit = current_app.config.get("EXPRESS_DELIVERY_WEIGHT_LIMIT_GRAMS", 5000)
        return self.weight_grams <= limit and self.stock > 0

    @property
    def delivery_label(self):
        from flask import current_app
        if self.is_express_eligible:
            return current_app.config.get("EXPRESS_DELIVERY_LABEL", "1-Hour Express")
        return current_app.config.get("STANDARD_DELIVERY_LABEL", "2-3 Day Standard")

    @property
    def discount_percent(self):
        if self.mrp and self.mrp > self.price:
            return round((1 - self.price / self.mrp) * 100)
        return 0

    @property
    def vehicle_label(self):
        return dict(VEHICLE_TYPES).get(self.vehicle_type, self.vehicle_type)

    @property
    def part_image_filename(self):
        """Return a local spare-part image based on the part name/category.

        Custom image_url values still take priority in storefront templates.
        This fallback keeps admin and storefront cards visually populated for
        parts added through the admin portal without requiring image hosting.
        """
        if self.category != "parts":
            return "parts-banner.jpg"

        text = f"{self.name or ''} {self.subcategory or ''}".lower()
        # Specific catalog items first, then generic category fallbacks.
        image_rules = (
            (("truck led fog lamp",), "truck-led-fog-lamp-set.jpg"),
            (("truck side mirror",), "truck-side-mirror-assembly.jpg"),
            (("truck brake drum",), "truck-brake-drum.jpg"),
            (("truck air filter",), "truck-air-filter-heavy-duty.jpg"),
            (("tempo headlamp assembly",), "tempo-headlamp-assembly.jpg"),
            (("tempo clutch plate",), "tempo-clutch-plate-heavy-duty.jpg"),
            (("auto-rickshaw led indicator",), "auto-rickshaw-led-indicator-set.jpg"),
            (("tempo leaf spring bush",), "tempo-leaf-spring-bush-kit.jpg"),
            (("auto-rickshaw side mirror",), "auto-rickshaw-side-mirror.jpg"),
            (("auto-rickshaw tyre",), "auto-rickshaw-tyre-tube-type.jpg"),
            (("auto-rickshaw clutch plate",), "auto-rickshaw-clutch-plate.jpg"),
            (("ev motor controller",), "ev-motor-controller.jpg"),
            (("ev battery pack",), "ev-battery-pack-48v.jpg"),
            (("ev onboard charger",), "ev-onboard-charger-cable.jpg"),
            (("scooter battery",), "scooter-battery-4ah.jpg"),
            (("front disc brake pad",), "front-disc-brake-pad.jpg"),
            (("scooter variator",), "scooter-variator-kit.jpg"),
            (("led headlamp bulb",), "led-headlamp-bulb.jpg"),
            (("clutch plate set",), "clutch-plate-set.jpg"),
            (("bike battery",), "bike-battery-5ah.jpg"),
            (("brake shoe set",), "brake-shoe-set.jpg"),
            (("chain & sprocket", "chain and sprocket"), "chain-sprocket-kit.jpg"),
            (("halogen headlight bulb",), "halogen-headlight-bulb-pair.jpg"),
            (("cabin air filter",), "cabin-air-filter.jpg"),
            (("engine oil filter",), "engine-oil-filter.jpg"),
            (("ceramic brake pad",), "ceramic-brake-pad-set-front.jpg"),
            (("brake pad", "brake pads"), "brake-pads.jpg"),
            (("brake disc", "brake drum", "disc brake"), "brake-disc.jpg"),
            (("oil filter",), "oil-filter.jpg"),
            (("air filter", "filter"), "air-filter.jpg"),
            (("spark plug", "spark"), "spark-plug.jpg"),
            (("timing belt",), "timing-belt.jpg"),
        )
        for keywords, filename in image_rules:
            if any(keyword in text for keyword in keywords):
                return filename
        return "parts-banner.jpg"

    @property
    def category_label(self):
        return dict(PRODUCT_CATEGORIES).get(self.category, self.category)

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def has_bulk_pricing(self):
        return bool(self.bulk_price and self.bulk_min_qty)

    def unit_price_for(self, quantity, account_type="individual"):
        """Business accounts ordering at/above the bulk threshold get bulk pricing."""
        if account_type == "business" and self.has_bulk_pricing and quantity >= self.bulk_min_qty:
            return self.bulk_price
        return self.price


# ---------------------------------------------------------------------------
# Cart (persisted per user so it survives across sessions/devices)
# ---------------------------------------------------------------------------

class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")

    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),)

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def unit_price(self, account_type="individual"):
        return self.product.unit_price_for(self.quantity, account_type)

    def line_total_for(self, account_type="individual"):
        return self.unit_price(account_type) * self.quantity


# ---------------------------------------------------------------------------
# Orders / Payments
# ---------------------------------------------------------------------------

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False, default=lambda: gen_code("AMX"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    order_type = db.Column(db.String(10), default="b2c")  # b2c | b2b — snapshot of buyer's account type
    status = db.Column(db.String(20), default="placed")
    delivery_type = db.Column(db.String(20), default="standard")  # express | standard
    delivery_address = db.Column(db.String(400))
    po_number = db.Column(db.String(60))  # optional purchase-order reference for business buyers

    subtotal = db.Column(db.Integer, default=0)
    delivery_fee = db.Column(db.Integer, default=0)
    discount = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)

    # Net-30 business credit orders
    is_credit_order = db.Column(db.Boolean, default=False)
    credit_due_date = db.Column(db.DateTime)
    credit_settled = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy="dynamic", cascade="all, delete-orphan")
    payment = db.relationship("Payment", backref="order", uselist=False, cascade="all, delete-orphan")

    @property
    def status_label(self):
        return self.status.replace("_", " ").title()

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product_name = db.Column(db.String(200))  # snapshot, survives product edits/deletes
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Integer, default=0)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    method = db.Column(db.String(20), nullable=False)  # upi | card | credit_card | emi | cod
    status = db.Column(db.String(20), default="pending")  # pending | success | failed
    transaction_id = db.Column(db.String(40))

    # EMI specifics (null for non-EMI payments)
    emi_tenure_months = db.Column(db.Integer)
    emi_monthly_amount = db.Column(db.Integer)
    emi_total_payable = db.Column(db.Integer)

    # Simulated instrument metadata (never store real card/UPI secrets like this in production)
    instrument_label = db.Column(db.String(80))  # e.g. "UPI: name@bank" or "Card ending 4242"

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def method_label(self):
        return dict(PAYMENT_METHODS).get(self.method, self.method)
