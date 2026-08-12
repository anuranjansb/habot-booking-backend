from datetime import datetime, timezone
from enum import Enum

from app.extensions import db


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class BookingRequest(db.Model):
    __tablename__ = "booking_requests"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("parents.id"),
        nullable=False,
        index=True,
    )

    lsa_id = db.Column(
        db.Integer,
        db.ForeignKey("lsa_profiles.id"),
        nullable=False,
        index=True,
    )

    start_time = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    end_time = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )

    status = db.Column(
        db.Enum(BookingStatus),
        nullable=False,
        default=BookingStatus.PENDING,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    parent = db.relationship(
        "Parent",
        backref=db.backref("bookings", lazy=True),
    )

    lsa = db.relationship(
        "LSAProfile",
        backref=db.backref("bookings", lazy=True),
    )
