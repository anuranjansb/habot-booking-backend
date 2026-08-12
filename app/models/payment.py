from datetime import datetime, timezone

from app.extensions import db


class PaymentEvent(db.Model):
    __tablename__ = "payment_events"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    event_id = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("booking_requests.id"),
        nullable=False,
        index=True,
    )

    status = db.Column(
        db.String(50),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
