from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    BookingRequest,
    BookingStatus,
    LSAProfile,
    Parent,
    User,
)


def create_lsa(app, email="lsa@test.com", active=True):
    with app.app_context():
        lsa = LSAProfile(
            name="Test LSA",
            email=email,
            skills=["ADHD", "Dyslexia"],
            is_active=active,
        )

        db.session.add(lsa)
        db.session.commit()

        return lsa.id


def test_create_booking(client, app, auth_user):
    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    lsa_id = create_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json

    assert data["parent_id"] == parent_id
    assert data["lsa_id"] == lsa_id
    assert data["status"] == "pending"


def test_reject_overlapping_booking(client, app, auth_user):
    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    lsa_id = create_lsa(app)

    first_response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=headers,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:30:00+00:00",
            "end_time": "2026-08-15T11:30:00+00:00",
        },
        headers=headers,
    )

    assert second_response.status_code == 409

    assert second_response.json["error"] == (
        "LSA is already booked for this time"
    )


def test_allow_back_to_back_booking(client, app, auth_user):
    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    lsa_id = create_lsa(app)

    first_response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=headers,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T11:00:00+00:00",
            "end_time": "2026-08-15T12:00:00+00:00",
        },
        headers=headers,
    )

    assert second_response.status_code == 201


def test_create_booking_missing_fields(client, auth_headers):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": 1,
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == "Missing required fields"


def test_create_booking_invalid_datetime(
    client,
    app,
    auth_user,
):
    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    lsa_id = create_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "invalid",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == "Invalid datetime format"


def test_create_booking_without_timezone(
    client,
    app,
    auth_user,
):
    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    lsa_id = create_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00",
            "end_time": "2026-08-15T11:00:00",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Datetime must include timezone information"
    )


def test_create_booking_end_before_start(
    client,
    app,
    auth_user,
):
    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    lsa_id = create_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T11:00:00+00:00",
            "end_time": "2026-08-15T10:00:00+00:00",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "end_time must be after start_time"
    )


def test_create_booking_parent_not_found(
    client,
    auth_headers,
):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": 9999,
            "lsa_id": 9999,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json["error"] == "Parent not found"


def test_get_booking_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/bookings/9999",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json["error"] == "Booking not found"


def test_create_booking_lsa_not_found(
    client,
    auth_user,
):
    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": 9999,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json["error"] == "LSA not found"


def test_create_booking_inactive_lsa(
    client,
    app,
    auth_user,
):
    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    lsa_id = create_lsa(
        app,
        email="inactive-lsa@test.com",
        active=False,
    )

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == "LSA is not active"


def test_create_booking_empty_body(client, auth_headers):
    response = client.post(
        "/api/v1/bookings/",
        json={},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == "Request body is required"


def test_database_prevents_overlapping_booking(app):
    with app.app_context():
        parent = Parent(
            name="DB Test Parent",
            email="db-parent@test.com",
        )

        lsa = LSAProfile(
            name="DB Test LSA",
            email="db-lsa@test.com",
            skills=["ADHD"],
            is_active=True,
        )

        db.session.add_all([parent, lsa])
        db.session.commit()

        first_booking = BookingRequest(
            parent_id=parent.id,
            lsa_id=lsa.id,
            start_time=datetime(
                2026,
                8,
                15,
                10,
                0,
                tzinfo=timezone.utc,
            ),
            end_time=datetime(
                2026,
                8,
                15,
                11,
                0,
                tzinfo=timezone.utc,
            ),
            status=BookingStatus.PENDING,
        )

        db.session.add(first_booking)
        db.session.commit()

        second_booking = BookingRequest(
            parent_id=parent.id,
            lsa_id=lsa.id,
            start_time=datetime(
                2026,
                8,
                15,
                10,
                30,
                tzinfo=timezone.utc,
            ),
            end_time=datetime(
                2026,
                8,
                15,
                11,
                30,
                tzinfo=timezone.utc,
            ),
            status=BookingStatus.PENDING,
        )

        db.session.add(second_booking)

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()


def test_create_booking_requires_auth(client):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": 1,
            "lsa_id": 1,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
    )

    assert response.status_code == 401


def test_get_booking_requires_auth(client):
    response = client.get(
        "/api/v1/bookings/1",
    )

    assert response.status_code == 401


def test_parent_cannot_access_another_parents_booking(
    client,
    app,
    auth_user,
):
    from flask_jwt_extended import create_access_token

    # Create another user + parent
    with app.app_context():
        other_user = User(
            email="other-parent@test.com",
            role="parent",
            is_active=True,
        )

        other_user.set_password("password123")

        db.session.add(other_user)
        db.session.flush()

        other_parent = Parent(
            name="Other Parent",
            email="other-parent-profile@test.com",
            user_id=other_user.id,
        )

        db.session.add(other_parent)
        db.session.commit()

        lsa = LSAProfile(
            name="Test LSA",
            email="ownership-lsa@test.com",
            skills=["ADHD"],
            is_active=True,
        )

        db.session.add(lsa)
        db.session.commit()

        booking = BookingRequest(
            parent_id=other_parent.id,
            lsa_id=lsa.id,
            start_time=datetime(
                2026,
                8,
                15,
                10,
                0,
                tzinfo=timezone.utc,
            ),
            end_time=datetime(
                2026,
                8,
                15,
                11,
                0,
                tzinfo=timezone.utc,
            ),
            status=BookingStatus.PENDING,
        )

        db.session.add(booking)
        db.session.commit()

        booking_id = booking.id

    response = client.get(
        f"/api/v1/bookings/{booking_id}",
        headers=auth_user["headers"],
    )

    assert response.status_code == 403
    assert response.json["error"] == "Forbidden"


def test_create_booking_invalid_parent_id_type(
    client,
    auth_headers,
):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": "abc",
            "lsa_id": 1,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_create_booking_invalid_lsa_id_type(
    client,
    auth_headers,
):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": 1,
            "lsa_id": "abc",
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_create_booking_negative_parent_id(
    client,
    auth_headers,
):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": -1,
            "lsa_id": 1,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_create_booking_negative_lsa_id(
    client,
    auth_headers,
):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": 1,
            "lsa_id": -1,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
