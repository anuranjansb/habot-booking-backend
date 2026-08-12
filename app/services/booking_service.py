from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import BookingRequest, BookingStatus, LSAProfile, Parent


class BookingError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def create_booking(
    parent_id,
    lsa_id,
    start_time,
    end_time,
):
    parent = db.session.get(Parent, parent_id)

    if not parent:
        raise BookingError("Parent not found", 404)

    lsa = db.session.get(LSAProfile, lsa_id)

    if not lsa:
        raise BookingError("LSA not found", 404)

    if not lsa.is_active:
        raise BookingError("LSA is not active", 400)

    if end_time <= start_time:
        raise BookingError(
            "end_time must be after start_time",
            400,
        )

    start_time = start_time.astimezone(timezone.utc)
    end_time = end_time.astimezone(timezone.utc)

    overlapping_booking = BookingRequest.query.filter(
        BookingRequest.lsa_id == lsa.id,
        BookingRequest.status.in_(
            [
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
            ]
        ),
        BookingRequest.start_time < end_time,
        BookingRequest.end_time > start_time,
    ).first()

    if overlapping_booking:
        raise BookingError(
            "LSA is already booked for this time",
            409,
        )

    booking = BookingRequest(
        parent_id=parent.id,
        lsa_id=lsa.id,
        start_time=start_time,
        end_time=end_time,
        status=BookingStatus.PENDING,
    )

    db.session.add(booking)

    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()

        if "booking_no_overlap" in str(error.orig):
            raise BookingError(
                "LSA is already booked for this time",
                409,
            )

        raise
    except Exception:
        db.session.rollback()
        raise

    return booking
