import os

from dotenv import load_dotenv
from flask import Flask
from app.routes.auth import auth_bp
from app.extensions import db, migrate
from flask_swagger_ui import get_swaggerui_blueprint
from flask_jwt_extended import JWTManager

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
    app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY",
        "dev-secret-change-this",
    )

    jwt = JWTManager(app)
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
        User,
    )

    from app.routes.bookings import bookings_bp
    from app.routes.lsas import lsas_bp
    from app.routes.payments import payments_bp

    app.register_blueprint(payments_bp)
    app.register_blueprint(lsas_bp)
    app.register_blueprint(bookings_bp)
    swaggerui_blueprint = get_swaggerui_blueprint(
        "/docs",
        "/static/openapi.yaml",
        config={
            "app_name": "HABOT Booking API",
        },
    )

    app.register_blueprint(swaggerui_blueprint)
    app.register_blueprint(auth_bp)
    return app
