from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import (
    BookingRequest,
    BookingStatus,
    PaymentEvent,
)
from app.services.payment_service import (
    PaymentGatewayError,
    verify_payment,
)


payments_bp = Blueprint(
    "payments",
    __name__,
    url_prefix="/api/v1/payments",
)


@payments_bp.post("/webhook")
def payment_webhook():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    event_id = data.get("event_id")
    booking_id = data.get("booking_id")
    payment_status = data.get("status")

    if not event_id or not booking_id or not payment_status:
        return jsonify({
            "error": (
                "event_id, booking_id and status are required"
            )
        }), 400

    if payment_status not in {"success", "failed"}:
        return jsonify({
            "error": "Invalid payment status"
        }), 400

    # Idempotency check
    existing_event = PaymentEvent.query.filter_by(
        event_id=event_id
    ).first()

    if existing_event:
        return jsonify({
            "booking_id": existing_event.booking_id,
            "status": existing_event.status,
            "message": "Event already processed",
        }), 200

    booking = db.session.get(
        BookingRequest,
        booking_id,
    )

    if not booking:
        return jsonify({
            "error": "Booking not found"
        }), 404

    if booking.status != BookingStatus.PENDING:
        return jsonify({
            "error": "Booking is not pending"
        }), 409

    # Verify payment with the mock external payment gateway.
    try:
        verified = verify_payment(
            event_id=event_id,
            booking_id=booking_id,
            payment_status=payment_status,
        )

    except PaymentGatewayError as error:
        return jsonify({
            "error": str(error)
        }), 502

    if not verified:
        return jsonify({
            "error": "Payment verification failed"
        }), 400

    if payment_status == "success":
        booking.status = BookingStatus.CONFIRMED
    else:
        booking.status = BookingStatus.FAILED

    payment_event = PaymentEvent(
        event_id=event_id,
        booking_id=booking.id,
        status=booking.status.value,
    )

    db.session.add(payment_event)

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "booking_id": booking.id,
        "status": booking.status.value,
    }), 200
