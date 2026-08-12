from datetime import datetime, timezone

from app.extensions import db
from app.models import (
    BookingRequest,
    BookingStatus,
    LSAProfile,
    Parent,
)


def create_pending_booking(app):
    with app.app_context():
        parent = Parent(
            name="Test Parent",
            email="payment-parent@test.com",
        )

        lsa = LSAProfile(
            name="Test LSA",
            email="payment-lsa@test.com",
            skills=["ADHD"],
            is_active=True,
        )

        db.session.add(parent)
        db.session.add(lsa)
        db.session.commit()

        booking = BookingRequest(
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

        db.session.add(booking)
        db.session.commit()

        return booking.id


def test_payment_success_confirms_booking(client, app):
    booking_id = create_pending_booking(app)

    response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_success_001",
            "booking_id": booking_id,
            "status": "success",
        },
    )

    assert response.status_code == 200
    assert response.json["booking_id"] == booking_id
    assert response.json["status"] == "confirmed"

    with app.app_context():
        booking = db.session.get(
            BookingRequest,
            booking_id,
        )

        assert booking.status == BookingStatus.CONFIRMED


def test_payment_failure_fails_booking(client, app):
    booking_id = create_pending_booking(app)

    response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_failed_001",
            "booking_id": booking_id,
            "status": "failed",
        },
    )

    assert response.status_code == 200
    assert response.json["booking_id"] == booking_id
    assert response.json["status"] == "failed"

    with app.app_context():
        booking = db.session.get(
            BookingRequest,
            booking_id,
        )

        assert booking.status == BookingStatus.FAILED


def test_duplicate_payment_event_is_idempotent(client, app):
    booking_id = create_pending_booking(app)

    payload = {
        "event_id": "evt_duplicate_001",
        "booking_id": booking_id,
        "status": "success",
    }

    first_response = client.post(
        "/api/v1/payments/webhook",
        json=payload,
    )

    assert first_response.status_code == 200
    assert first_response.json["status"] == "confirmed"

    second_response = client.post(
        "/api/v1/payments/webhook",
        json=payload,
    )

    assert second_response.status_code == 200
    assert second_response.json["booking_id"] == booking_id
    assert second_response.json["status"] == "confirmed"
    assert second_response.json["message"] == "Event already processed"


def test_invalid_payment_status_returns_400(client, app):
    booking_id = create_pending_booking(app)

    response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_invalid_001",
            "booking_id": booking_id,
            "status": "pending",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "Invalid payment status"


def test_payment_for_missing_booking_returns_404(client):
    response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_missing_001",
            "booking_id": 99999,
            "status": "success",
        },
    )

    assert response.status_code == 404
    assert response.json["error"] == "Booking not found"


def test_payment_for_already_confirmed_booking_returns_409(client, app):
    booking_id = create_pending_booking(app)

    first_response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_confirmed_001",
            "booking_id": booking_id,
            "status": "success",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_confirmed_002",
            "booking_id": booking_id,
            "status": "success",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json["error"] == "Booking is not pending"
