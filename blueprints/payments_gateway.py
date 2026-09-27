"""
Payment processing for AutoMart.

This module is intentionally isolated so that going live later means
editing ONLY this file, not the checkout views or templates.

Current mode: SIMULATED. Every method below returns a realistic-looking
success/failure without moving real money, so the full checkout UX
(UPI / Card / Credit Card / EMI / COD) can be demoed end-to-end.

To go live with Razorpay (recommended for Indian UPI + cards + EMI):
1. `pip install razorpay`
2. Set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET as real env vars.
3. Replace `process_payment()` body with an order-create + signature
   verification flow per Razorpay's Python SDK docs.
4. Flip Config.PAYMENT_LIVE_MODE to True once verified in a sandbox.
5. COD needs no gateway — it just marks the order for pay-on-delivery.
"""
import random
import string
from datetime import datetime

from flask import current_app


def _txn_id(prefix):
    chars = string.ascii_uppercase + string.digits
    return f"{prefix}{''.join(random.choices(chars, k=12))}"


def calculate_emi(principal, annual_rate_percent, tenure_months):
    """Simple-interest EMI approximation, fine for demo/estimate purposes."""
    r = annual_rate_percent / 100 / 12
    if r == 0:
        monthly = principal / tenure_months
    else:
        monthly = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    monthly = round(monthly)
    total = monthly * tenure_months
    return monthly, total


def get_emi_options(principal):
    """Return a list of {tenure, monthly, total, interest} for the checkout page."""
    rate = current_app.config.get("EMI_ANNUAL_INTEREST_RATE", 14.0)
    options = []
    for tenure in current_app.config.get("EMI_TENURES_MONTHS", [3, 6, 9, 12]):
        monthly, total = calculate_emi(principal, rate, tenure)
        options.append({
            "tenure": tenure,
            "monthly": monthly,
            "total": total,
            "interest": total - principal,
        })
    return options


def process_payment(method, amount, instrument_label=None, emi_tenure=None):
    """
    Simulate contacting a payment gateway.

    Returns dict: { success: bool, transaction_id: str|None,
                     status: 'success'|'failed'|'pending', message: str }

    COD never "fails" here — it's confirmed on delivery, not at checkout.
    Card/UPI/Credit Card/EMI succeed the large majority of the time in
    the simulation (a small failure chance keeps the failure/retry UI
    reachable during a demo).
    """
    if current_app.config.get("PAYMENT_LIVE_MODE"):
        raise NotImplementedError(
            "PAYMENT_LIVE_MODE is on but no real gateway is wired up yet. "
            "Implement the real call in payments_gateway.process_payment()."
        )

    if method == "cod":
        return {
            "success": True,
            "transaction_id": None,
            "status": "pending",
            "message": "Order confirmed. Pay in cash when it arrives.",
        }

    if method == "credit_terms":
        return {
            "success": True,
            "transaction_id": None,
            "status": "pending",
            "message": "Order placed on Net 30 business credit. Invoice due in 30 days.",
        }

    # Simulate a brief, mostly-successful gateway round trip.
    failure_roll = random.random()
    if failure_roll < 0.05:
        return {
            "success": False,
            "transaction_id": None,
            "status": "failed",
            "message": "Payment declined by your bank. Please try another method.",
        }

    prefix = {"upi": "UPI", "card": "CRD", "credit_card": "CCD", "emi": "EMI"}.get(method, "TXN")
    return {
        "success": True,
        "transaction_id": _txn_id(prefix),
        "status": "success",
        "message": "Payment successful.",
    }
