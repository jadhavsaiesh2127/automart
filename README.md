# AutoMart — Vehicle Parts & Accessories Marketplace (B2B + B2C)

A Flask web app for an entrepreneurship project: spare parts and accessories
for **cars, motorcycles, scooters, EVs, auto-rickshaws, tempos, and small
trucks**, with 1-Hour Express delivery on lightweight items, a full Indian
payment stack (UPI, Debit Card, Credit Card, EMI, COD), and a B2B track
(tiered bulk pricing + Net-30 business credit) alongside normal retail (B2C).

## What's included

- **Storefront** — browse by vehicle type or category (Parts / Accessories),
  search, sort, product detail pages, cart, checkout, order tracking.
- **B2C** — individual accounts, retail pricing, all payment methods.
- **B2B** — business accounts (garage / retailer / fleet / distributor) with
  GSTIN, automatic tiered/bulk pricing above a quantity threshold, PO number
  on checkout, and Net-30 invoice-on-credit checkout once an admin verifies
  the account and sets a credit limit.
- **Payments** — UPI, Debit Card, Credit Card, EMI (with a live monthly
  installment calculator), Cash on Delivery, and Business Credit (Net 30).
  Payment processing is **simulated** end-to-end (see "Going live" below).
- **Delivery logic** — items ≤5kg qualify automatically for 1-Hour Express;
  heavier items ship Standard (2–3 days). Free delivery over ₹999.
- **Admin dashboard** — revenue split by B2B/B2C, pending orders, low stock,
  full product CRUD (including bulk-pricing fields), order status management,
  and a customers view to verify business accounts + set credit limits.

## Project structure

```
automart/
  app.py                  # Flask app factory + entrypoint
  config.py                # Settings (delivery fees, EMI rate, etc.)
  extensions.py             # db, login_manager
  models.py                 # User, Product, Cart, Order, Payment
  seed.py                   # Demo data — run this once
  blueprints/
    auth.py                 # login / register / logout
    storefront.py            # browsing, cart, checkout, payment, orders
    admin.py                 # dashboard, product & order & customer mgmt
    payments_gateway.py       # ⚠️ isolated payment logic — edit this to go live
  templates/                 # Jinja2 templates (storefront/, admin/, auth/)
  static/                    # CSS + JS
```

## Running it locally

```bash
cd automart
pip install -r requirements.txt
python seed.py        # creates the database and demo data (run once)
python app.py          # starts the dev server on http://localhost:5000
```

### Demo logins (created by seed.py)

| Role                       | Email                          | Password     |
|----------------------------|---------------------------------|--------------|
| Admin                      | admin@automart.in               | admin123     |
| Individual customer (B2C)  | priya@example.com               | password123  |
| Verified business (B2B)    | fleet@sharmaautoworks.in        | password123  |
| Unverified business (B2B)  | pending@rkdistributors.in       | password123  |

The "verified business" account already has a ₹1,00,000 credit limit, so you
can test the Net-30 "Business Credit" payment option immediately. The
"unverified business" account shows what a new B2B signup looks like before
an admin approves it (visit **Admin → Customers → Business** to verify one).

## Going live later

This build is structured so launching for real means editing a few specific
files, not rewriting the app:

1. **Payments** — `blueprints/payments_gateway.py` currently simulates every
   transaction. Swap in a real Indian payment gateway (Razorpay is a common
   choice — it supports UPI, cards, and EMI in one integration) by replacing
   `process_payment()`. Comments in that file point to what's needed.
2. **Database** — swap `SQLALCHEMY_DATABASE_URI` in `config.py` from SQLite
   to a managed Postgres/MySQL instance.
3. **Secrets** — move `SECRET_KEY` and gateway keys to real environment
   variables (never commit them).
4. **Images** — product `image_url` fields currently expect a plain URL;
   swap for real product photography or an S3/Cloudinary bucket.
5. **GST invoicing** — GSTIN is captured on business accounts; for real
   compliance you'll want proper tax-invoice PDF generation per order.

## Notes on the payment simulation

Every payment method walks through a realistic UI (enter UPI ID / card
details / choose EMI tenure) and returns a simulated success/failure so the
full checkout experience can be demoed without a live merchant account —
setting one up requires business registration and bank approval, which is
outside the scope of a prototype. COD and Business Credit never "fail" at
checkout since neither moves money electronically at that point.
