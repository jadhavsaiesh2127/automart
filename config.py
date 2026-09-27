import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Central configuration. Values here are safe defaults for local
    development / a college demo. When you actually launch:

    - Move SECRET_KEY, DATABASE_URL, and gateway keys into real
      environment variables (never commit them).
    - Swap SQLALCHEMY_DATABASE_URI for a managed Postgres/MySQL URL.
    - Set PAYMENT_LIVE_MODE = True only once you've wired a real
      gateway in blueprints/payments_gateway.py (see comments there).
    """
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-this-before-launch")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'automart.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Spare-part image uploads
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per request
    ALLOWED_PART_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # Business rules
    CURRENCY_SYMBOL = "₹"
    EXPRESS_DELIVERY_LABEL = "1-Hour Express"
    EXPRESS_DELIVERY_WEIGHT_LIMIT_GRAMS = 5000  # items under 5kg qualify for 1-hr delivery
    STANDARD_DELIVERY_LABEL = "2-3 Day Standard"
    EXPRESS_DELIVERY_FEE = 49
    STANDARD_DELIVERY_FEE = 0
    FREE_DELIVERY_THRESHOLD = 999

    # EMI configuration (simple-interest simulation for the prototype)
    EMI_TENURES_MONTHS = [3, 6, 9, 12]
    EMI_ANNUAL_INTEREST_RATE = 14.0  # percent, typical no-cost/low-cost card EMI range
    EMI_MIN_ORDER_VALUE = 1500

    # Payment gateway — placeholders only. This build simulates a
    # successful/failed outcome so the full UX can be demoed end-to-end.
    # To go live, plug real credentials + SDKs here (e.g. Razorpay/Paytm/PayU)
    # and replace the logic in blueprints/payments_gateway.py.
    PAYMENT_LIVE_MODE = False
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
