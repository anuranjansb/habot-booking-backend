from datetime import datetime, timezone

from app.extensions import db


class LSAProfile(db.Model):
    __tablename__ = "lsa_profiles"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False,
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    skills = db.Column(
        db.ARRAY(db.String(100)),
        nullable=False,
        default=list,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
