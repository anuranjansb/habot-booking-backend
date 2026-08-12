def create_parent_and_lsa(app):
    from app.extensions import db
    from app.models import LSAProfile, Parent

    with app.app_context():
        parent = Parent(
            name="Test Parent",
            email="parent@test.com",
        )

        lsa = LSAProfile(
            name="Test LSA",
            email="lsa@test.com",
            skills=["ADHD", "Dyslexia"],
            is_active=True,
        )

        db.session.add(parent)
        db.session.add(lsa)
        db.session.commit()

        return parent.id, lsa.id


def test_create_booking(client, app):
    parent_id, lsa_id = create_parent_and_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
    )

    assert response.status_code == 201

    data = response.json

    assert data["parent_id"] == parent_id
    assert data["lsa_id"] == lsa_id
    assert data["status"] == "pending"


def test_reject_overlapping_booking(client, app):
    parent_id, lsa_id = create_parent_and_lsa(app)

    first_response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
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
    )

    assert second_response.status_code == 409

    assert second_response.json["error"] == (
        "LSA is already booked for this time"
    )


def test_allow_back_to_back_booking(client, app):
    parent_id, lsa_id = create_parent_and_lsa(app)

    first_response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
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
    )

    assert second_response.status_code == 201


def test_create_booking_missing_fields(client):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": 1,
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "Missing required fields"


def test_create_booking_invalid_datetime(client, app):
    parent_id, lsa_id = create_parent_and_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "invalid",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "Invalid datetime format"


def test_create_booking_without_timezone(client, app):
    parent_id, lsa_id = create_parent_and_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00",
            "end_time": "2026-08-15T11:00:00",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Datetime must include timezone information"
    )


def test_create_booking_end_before_start(client, app):
    parent_id, lsa_id = create_parent_and_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T11:00:00+00:00",
            "end_time": "2026-08-15T10:00:00+00:00",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "end_time must be after start_time"
    )


def test_create_booking_parent_not_found(client):
    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": 9999,
            "lsa_id": 9999,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
    )

    assert response.status_code == 404
    assert response.json["error"] == "Parent not found"


def test_get_booking_not_found(client):
    response = client.get(
        "/api/v1/bookings/9999"
    )

    assert response.status_code == 404
    assert response.json["error"] == "Booking not found"


def test_create_booking_lsa_not_found(client, app):
    parent_id, _ = create_parent_and_lsa(app)

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": 9999,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
    )

    assert response.status_code == 404
    assert response.json["error"] == "LSA not found"


def test_create_booking_inactive_lsa(client, app):
    from app.extensions import db
    from app.models import LSAProfile, Parent

    with app.app_context():
        parent = Parent(
            name="Test Parent",
            email="inactive-parent@test.com",
        )

        lsa = LSAProfile(
            name="Inactive LSA",
            email="inactive-lsa@test.com",
            skills=["ADHD"],
            is_active=False,
        )

        db.session.add(parent)
        db.session.add(lsa)
        db.session.commit()

        parent_id = parent.id
        lsa_id = lsa.id

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "LSA is not active"


def test_create_booking_empty_body(client):
    response = client.post(
        "/api/v1/bookings/",
        json={},
    )

    assert response.status_code == 400
    assert response.json["error"] == "Request body is required"


def test_database_prevents_overlapping_booking(app):
    from datetime import datetime, timezone
    import pytest
    from app.extensions import db
    from app.models import (
        BookingRequest,
        BookingStatus,
        LSAProfile,
        Parent,
    )
    from sqlalchemy.exc import IntegrityError

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
                2026, 8, 15, 10, 0,
                tzinfo=timezone.utc,
            ),
            end_time=datetime(
                2026, 8, 15, 11, 0,
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
                2026, 8, 15, 10, 30,
                tzinfo=timezone.utc,
            ),
            end_time=datetime(
                2026, 8, 15, 11, 30,
                tzinfo=timezone.utc,
            ),
            status=BookingStatus.PENDING,
        )

        db.session.add(second_booking)

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()
