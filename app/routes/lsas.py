from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models import BookingRequest, BookingStatus, LSAProfile
from app.auth import role_required

lsas_bp = Blueprint(
    "lsas",
    __name__,
    url_prefix="/api/v1/lsas",
)


@lsas_bp.get("/search/")
@jwt_required()
@role_required("parent")
def search_lsas():
    skill = request.args.get("skill")
    if skill is not None:
        skill = skill.strip()

        if not skill:
            return jsonify({
                "error": "skill must not be empty"
            }), 400
    start_time_str = request.args.get("start_time")
    end_time_str = request.args.get("end_time")

    query = LSAProfile.query.filter(
        LSAProfile.is_active.is_(True)
    )

    if skill:
        query = query.filter(
            LSAProfile.skills.any(skill)
        )

    if start_time_str is not None:
        start_time_str = start_time_str.strip()

    if end_time_str is not None:
        end_time_str = end_time_str.strip()

    if start_time_str or end_time_str:
        if not start_time_str or not end_time_str:
            return jsonify({
                "error": (
                    "start_time and end_time "
                    "must be provided together"
                )
            }), 400

        try:
            start_time = datetime.fromisoformat(
                start_time_str.replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(
                end_time_str.replace("Z", "+00:00")
            )
        except ValueError:
            return jsonify({
                "error": "Invalid datetime format"
            }), 400

        if start_time.tzinfo is None or end_time.tzinfo is None:
            return jsonify({
                "error": "Datetime must include timezone information"
            }), 400

        if end_time <= start_time:
            return jsonify({
                "error": "end_time must be after start_time"
            }), 400

        unavailable_lsa_ids = select(
            BookingRequest.lsa_id
        ).where(
            BookingRequest.status.in_([
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
            ]),
            BookingRequest.start_time < end_time,
            BookingRequest.end_time > start_time,
        )

        query = query.filter(
            ~LSAProfile.id.in_(unavailable_lsa_ids)
        )

    lsas = query.all()

    return jsonify([
        {
            "id": lsa.id,
            "name": lsa.name,
            "email": lsa.email,
            "skills": lsa.skills,
            "is_active": lsa.is_active,
        }
        for lsa in lsas
    ])
