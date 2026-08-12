from datetime import datetime, timezone
from unittest.mock import patch

import requests

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


def mock_successful_gateway(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "verified": True,
    }


@patch("app.services.payment_service.requests.post")
def test_payment_success_confirms_booking(
    mock_post,
    client,
    app,
):
    mock_successful_gateway(mock_post)

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

    mock_post.assert_called_once()

    with app.app_context():
        booking = db.session.get(
            BookingRequest,
            booking_id,
        )

        assert booking.status == BookingStatus.CONFIRMED


@patch("app.services.payment_service.requests.post")
def test_payment_failure_fails_booking(
    mock_post,
    client,
    app,
):
    mock_successful_gateway(mock_post)

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

    mock_post.assert_called_once()

    with app.app_context():
        booking = db.session.get(
            BookingRequest,
            booking_id,
        )

        assert booking.status == BookingStatus.FAILED


@patch("app.services.payment_service.requests.post")
def test_duplicate_payment_event_is_idempotent(
    mock_post,
    client,
    app,
):
    mock_successful_gateway(mock_post)

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

    # The external service should only be called once.
    mock_post.assert_called_once()


def test_invalid_payment_status_returns_400(
    client,
    app,
):
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


@patch("app.services.payment_service.requests.post")
def test_payment_for_already_confirmed_booking_returns_409(
    mock_post,
    client,
    app,
):
    mock_successful_gateway(mock_post)

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

    mock_post.assert_called_once()


@patch("app.services.payment_service.requests.post")
def test_payment_gateway_failure_returns_502(
    mock_post,
    client,
    app,
):
    mock_post.side_effect = requests.RequestException(
        "Payment gateway unavailable"
    )

    booking_id = create_pending_booking(app)

    response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_gateway_failure_001",
            "booking_id": booking_id,
            "status": "success",
        },
    )

    assert response.status_code == 502
    assert response.json["error"] == (
        "Payment gateway unavailable"
    )

    with app.app_context():
        booking = db.session.get(
            BookingRequest,
            booking_id,
        )

        assert booking.status == BookingStatus.PENDING


@patch("app.services.payment_service.requests.post")
def test_payment_gateway_verification_failure_returns_400(
    mock_post,
    client,
    app,
):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "verified": False,
    }

    booking_id = create_pending_booking(app)

    response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_verification_failure_001",
            "booking_id": booking_id,
            "status": "success",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Payment verification failed"
    )

    with app.app_context():
        booking = db.session.get(
            BookingRequest,
            booking_id,
        )

        assert booking.status == BookingStatus.PENDING


@patch("app.services.payment_service.requests.post")
def test_payment_gateway_invalid_response_returns_502(
    mock_post,
    client,
    app,
):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.side_effect = ValueError(
        "Invalid JSON"
    )

    booking_id = create_pending_booking(app)

    response = client.post(
        "/api/v1/payments/webhook",
        json={
            "event_id": "evt_invalid_gateway_response_001",
            "booking_id": booking_id,
            "status": "success",
        },
    )

    assert response.status_code == 502
    assert response.json["error"] == (
        "Invalid payment gateway response"
    )

    with app.app_context():
        booking = db.session.get(
            BookingRequest,
            booking_id,
        )

        assert booking.status == BookingStatus.PENDING
