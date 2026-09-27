"""
Populate AutoMart with demo data: an admin account, a few customer
accounts (individual + business), and a product catalog spanning every
vehicle type and both categories (parts / accessories).

Run once after installing dependencies:
    python seed.py
"""
from app import create_app
from extensions import db
from models import User, Product, gen_code

app = create_app()

PRODUCTS = [
    # (name, brand, category, vehicle_type, subcategory, price, mrp, stock, weight_g, bulk_price, bulk_min_qty)
    ("Ceramic Brake Pad Set — Front", "Bosch", "parts", "car", "Brakes", 1499, 1899, 40, 900, 1250, 10),
    ("Engine Oil Filter", "Mahle", "parts", "car", "Filters", 349, 449, 120, 180, 280, 25),
    ("Cabin Air Filter", "Bosch", "parts", "car", "Filters", 599, 799, 80, 150, 480, 20),
    ("Halogen Headlight Bulb (Pair)", "Philips", "parts", "car", "Lighting", 799, 999, 60, 120, 640, 15),
    ("Windshield Wiper Blade Set", "Bosch", "accessories", "car", "Exterior", 899, 1199, 70, 300, 720, 12),
    ("Car Body Cover — Waterproof", "AutoFurnish", "accessories", "car", "Protection", 1299, 1699, 35, 800, None, None),
    ("Dashboard Camera — 1080p", "70mai", "accessories", "car", "Electronics", 3499, 4299, 25, 350, 2999, 5),

    ("Chain & Sprocket Kit", "Rox", "parts", "bike", "Drivetrain", 1199, 1499, 55, 1200, 999, 10),
    ("Brake Shoe Set", "TVS Genuine", "parts", "bike", "Brakes", 349, 449, 90, 300, 290, 25),
    ("Bike Battery — 5Ah", "Amaron", "parts", "bike", "Electrical", 1099, 1399, 45, 1800, 950, 10),
    ("Clutch Plate Set", "Bajaj Genuine", "parts", "bike", "Engine", 799, 999, 50, 700, 670, 15),
    ("Bike Cover — All Weather", "AutoFurnish", "accessories", "bike", "Protection", 499, 649, 100, 250, 410, 20),
    ("Handlebar Grip Set", "Rox", "accessories", "bike", "Comfort", 299, 399, 150, 120, 240, 30),
    ("LED Headlamp Bulb", "Philips", "parts", "bike", "Lighting", 449, 599, 70, 90, 370, 20),

    ("Scooter Variator Kit", "GY6", "parts", "scooter", "Drivetrain", 1399, 1699, 30, 900, 1180, 8),
    ("Scooter Seat Cover", "AutoFurnish", "accessories", "scooter", "Comfort", 349, 449, 90, 250, 290, 20),
    ("Front Disc Brake Pad", "TVS Genuine", "parts", "scooter", "Brakes", 399, 499, 65, 280, 330, 20),
    ("Scooter Under-seat Storage Hook", "Autofit", "accessories", "scooter", "Storage", 149, 199, 200, 60, 110, 40),
    ("Scooter Battery — 4Ah", "Exide", "parts", "scooter", "Electrical", 949, 1199, 40, 1600, 820, 10),

    ("EV Onboard Charger Cable", "Ather", "parts", "ev", "Charging", 2499, 2999, 20, 900, 2150, 5),
    ("EV Battery Pack — 48V", "Okinawa", "parts", "ev", "Battery", 18999, 21999, 8, 12000, 17500, 3),
    ("EV Motor Controller", "Bosch", "parts", "ev", "Electrical", 4599, 5299, 12, 1400, 3999, 4),
    ("EV Charging Port Cover", "Ather", "accessories", "ev", "Protection", 249, 329, 80, 60, 199, 25),
    ("EV Dashboard Mobile Mount", "Autofit", "accessories", "ev", "Comfort", 399, 499, 60, 150, 320, 20),

    ("Auto-Rickshaw Clutch Plate", "Bajaj Genuine", "parts", "auto_rickshaw", "Drivetrain", 899, 1099, 35, 1100, 760, 10),
    ("Auto-Rickshaw Tyre — Tube Type", "MRF", "parts", "auto_rickshaw", "Tyres", 2199, 2599, 25, 4500, 1950, 6),
    ("Auto-Rickshaw Seat Cover Set", "AutoFurnish", "accessories", "auto_rickshaw", "Comfort", 799, 999, 50, 900, 660, 12),
    ("Auto-Rickshaw Side Mirror", "Autofit", "parts", "auto_rickshaw", "Body", 249, 329, 90, 300, 200, 25),
    ("Auto-Rickshaw LED Indicator Set", "Philips", "parts", "auto_rickshaw", "Lighting", 549, 699, 60, 200, 460, 20),

    ("Tempo Leaf Spring Bush Kit", "Lucas TVS", "parts", "tempo", "Suspension", 1699, 1999, 22, 3200, 1450, 6),
    ("Tempo Clutch Plate — Heavy Duty", "Valeo", "parts", "tempo", "Drivetrain", 2399, 2799, 18, 3800, 2050, 5),
    ("Tempo Tarpaulin Cover", "AutoFurnish", "accessories", "tempo", "Protection", 1899, 2299, 20, 6000, 1600, 5),
    ("Tempo Headlamp Assembly", "Lucas TVS", "parts", "tempo", "Lighting", 1199, 1499, 28, 900, 1000, 8),

    ("Truck Air Filter — Heavy Duty", "Mahle", "parts", "truck", "Filters", 999, 1299, 40, 1500, 850, 12),
    ("Truck Brake Drum", "Setco", "parts", "truck", "Brakes", 3299, 3899, 14, 8000, 2900, 4),
    ("Truck Side Mirror Assembly", "Lucas TVS", "parts", "truck", "Body", 899, 1099, 30, 700, 750, 10),
    ("Truck Seat Cover — Heavy Duty", "AutoFurnish", "accessories", "truck", "Comfort", 1499, 1799, 25, 2200, 1250, 8),
    ("Truck LED Fog Lamp Set", "Philips", "parts", "truck", "Lighting", 1899, 2299, 20, 900, 1600, 6),
]


def run():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(email="admin@automart.in").first():
            admin = User(name="AutoMart Admin", email="admin@automart.in", role="admin", account_type="individual")
            admin.set_password("admin123")
            db.session.add(admin)

        if not User.query.filter_by(email="priya@example.com").first():
            priya = User(
                name="Priya Sharma", email="priya@example.com", phone="9876543210",
                city="Pune", state="Maharashtra", pincode="411001",
                address_line="12 MG Road", account_type="individual",
            )
            priya.set_password("password123")
            db.session.add(priya)

        if not User.query.filter_by(email="fleet@sharmaautoworks.in").first():
            business = User(
                name="Ravi Sharma", email="fleet@sharmaautoworks.in", phone="9123456780",
                city="Nagpur", state="Maharashtra", pincode="440001",
                address_line="Plot 4, Industrial Area",
                account_type="business", company_name="Sharma Auto Works",
                gst_number="27AAAAA0000A1Z5", business_type="garage",
                business_verified=True, credit_limit=100000, credit_used=0,
            )
            business.set_password("password123")
            db.session.add(business)

        if not User.query.filter_by(email="pending@rkdistributors.in").first():
            pending_business = User(
                name="Kavita Rao", email="pending@rkdistributors.in", phone="9988776655",
                city="Indore", state="Madhya Pradesh", pincode="452001",
                account_type="business", company_name="RK Auto Distributors",
                gst_number="23BBBBB1111B2Z6", business_type="distributor",
                business_verified=False,
            )
            pending_business.set_password("password123")
            db.session.add(pending_business)

        db.session.commit()

        if Product.query.count() == 0:
            for row in PRODUCTS:
                (name, brand, category, vehicle_type, subcat, price, mrp, stock,
                 weight_g, bulk_price, bulk_min_qty) = row
                slug = "-".join(name.lower().replace("—", "-").split())
                p = Product(
                    sku=gen_code("SKU", 6),
                    name=name, slug=slug, brand=brand, category=category,
                    vehicle_type=vehicle_type, subcategory=subcat,
                    price=price, mrp=mrp, stock=stock, weight_grams=weight_g,
                    bulk_price=bulk_price, bulk_min_qty=bulk_min_qty,
                    rating=4.0 + (hash(name) % 10) / 20,
                    description=f"{brand} {name.lower()} — compatible with common {vehicle_type.replace('_', ' ')} models sold in India.",
                )
                db.session.add(p)
            db.session.commit()

        print("Seed complete.")
        print(" Admin login:            admin@automart.in / admin123")
        print(" Individual login:       priya@example.com / password123")
        print(" Verified business:      fleet@sharmaautoworks.in / password123 (Net 30 credit unlocked)")
        print(" Pending business:       pending@rkdistributors.in / password123 (awaiting admin verification)")


if __name__ == "__main__":
    run()
