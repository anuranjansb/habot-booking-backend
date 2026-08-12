from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import BookingRequest
from app.services.booking_service import (
    BookingError,
    create_booking as create_booking_service,
)


bookings_bp = Blueprint(
    "bookings",
    __name__,
    url_prefix="/api/v1/bookings",
)


@bookings_bp.post("/")
def create_booking():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    required_fields = [
        "parent_id",
        "lsa_id",
        "start_time",
        "end_time",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields,
        }), 400

    try:
        start_time = datetime.fromisoformat(
            data["start_time"].replace("Z", "+00:00")
        )
        end_time = datetime.fromisoformat(
            data["end_time"].replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return jsonify({
            "error": "Invalid datetime format"
        }), 400

    if start_time.tzinfo is None or end_time.tzinfo is None:
        return jsonify({
            "error": "Datetime must include timezone information"
        }), 400

    try:
        booking = create_booking_service(
            parent_id=data["parent_id"],
            lsa_id=data["lsa_id"],
            start_time=start_time,
            end_time=end_time,
        )

    except BookingError as error:
        return jsonify({
            "error": error.message
        }), error.status_code

    return jsonify({
        "id": booking.id,
        "parent_id": booking.parent_id,
        "lsa_id": booking.lsa_id,
        "start_time": booking.start_time.isoformat(),
        "end_time": booking.end_time.isoformat(),
        "status": booking.status.value,
    }), 201


@bookings_bp.get("/<int:booking_id>")
def get_booking(booking_id):
    booking = db.session.get(
        BookingRequest,
        booking_id,
    )

    if not booking:
        return jsonify({
            "error": "Booking not found"
        }), 404

    return jsonify({
        "id": booking.id,
        "parent_id": booking.parent_id,
        "lsa_id": booking.lsa_id,
        "start_time": booking.start_time.isoformat(),
        "end_time": booking.end_time.isoformat(),
        "status": booking.status.value,
    }), 200
