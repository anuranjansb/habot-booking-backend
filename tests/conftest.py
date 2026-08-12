import pytest

from flask_jwt_extended import create_access_token
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import Parent, User


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
        db.drop_all()
        db.create_all()

        # Required for PostgreSQL GIST equality on integer lsa_id.
        db.session.execute(
            text(
                """
                CREATE EXTENSION IF NOT EXISTS btree_gist;
                """
            )
        )

        # Recreate the same database-level protection used in production.
        db.session.execute(
            text(
                """
                ALTER TABLE booking_requests
                ADD CONSTRAINT booking_no_overlap
                EXCLUDE USING gist (
                    lsa_id WITH =,
                    tstzrange(
                        start_time,
                        end_time,
                        '[)'
                    ) WITH &&
                )
                WHERE (
                    status IN ('PENDING', 'CONFIRMED')
                );
                """
            )
        )

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_user(app):
    with app.app_context():
        user = User(
            email="test-auth@example.com",
            role="parent",
            is_active=True,
        )

        user.set_password("testpassword123")

        db.session.add(user)
        db.session.flush()

        parent = Parent(
            name="Authenticated Test Parent",
            email="authenticated-parent@example.com",
            user_id=user.id,
        )

        db.session.add(parent)
        db.session.commit()

        token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "role": "parent",
            },
        )

        return {
            "user_id": user.id,
            "parent_id": parent.id,
            "headers": {
                "Authorization": f"Bearer {token}",
            },
        }


@pytest.fixture()
def auth_headers(auth_user):
    return auth_user["headers"]
