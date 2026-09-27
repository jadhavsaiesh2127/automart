import os
from flask import Flask
from extensions import db, login_manager
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from blueprints.auth import bp as auth_bp
    from blueprints.storefront import bp as storefront_bp
    from blueprints.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(storefront_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from models import CartItem, VEHICLE_TYPES, PRODUCT_CATEGORIES
        cart_count = 0
        if current_user.is_authenticated:
            cart_count = sum(i.quantity for i in CartItem.query.filter_by(user_id=current_user.id).all())
        return dict(
            currency=app.config.get("CURRENCY_SYMBOL", "₹"),
            cart_count=cart_count,
            nav_vehicle_types=VEHICLE_TYPES,
            nav_categories=PRODUCT_CATEGORIES,
        )

    @app.errorhandler(403)
    def forbidden(e):
        return render_error(app, "403", "You don't have access to this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_error(app, "404", "That page took a wrong turn."), 404

    with app.app_context():
        db.create_all()

    return app


def render_error(app, code, message):
    from flask import render_template
    return render_template("error.html", code=code, message=message)


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
