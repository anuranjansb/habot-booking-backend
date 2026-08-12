import pytest
from sqlalchemy import text
from flask_migrate import upgrade

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": (
                "postgresql://postgres:postgres"
                "@localhost:5432/habot_booking_test"
            ),
        }
    )

    with app.app_context():
        # Clean the test database
        db.drop_all()

        # Remove Alembic's version table if it exists
        db.session.execute(
            text("DROP TABLE IF EXISTS alembic_version CASCADE")
        )
        db.session.commit()

        # Apply all Alembic migrations
        upgrade(directory="migrations")

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
