import os

from dotenv import load_dotenv
from flask import Flask

from app.extensions import db, migrate

load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__)

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        database_url = (
            f"postgresql://{os.getenv('POSTGRES_USER')}:"
            f"{os.getenv('POSTGRES_PASSWORD')}@"
            f"{os.getenv('POSTGRES_HOST')}:"
            f"{os.getenv('POSTGRES_PORT')}/"
            f"{os.getenv('POSTGRES_DB')}"
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return {
            "error": error.name,
            "message": error.description,
        }, error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled exception")

        return {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
        }, 500

    from app.models import (
        BookingRequest,
        LSAProfile,
        Parent,
        PaymentEvent,
    )

    from app.routes.bookings import bookings_bp
    from app.routes.lsas import lsas_bp
    from app.routes.payments import payments_bp

    app.register_blueprint(payments_bp)
    app.register_blueprint(lsas_bp)
    app.register_blueprint(bookings_bp)

    return app
