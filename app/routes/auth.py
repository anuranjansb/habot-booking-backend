from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import User


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/v1/auth",
)


@auth_bp.post("/register")
def register():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    required_fields = [
        "email",
        "password",
        "role",
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

    email = data["email"].strip().lower()
    password = data["password"]
    role = data["role"].lower()

    if not email:
        return jsonify({
            "error": "Email is required"
        }), 400

    if not password:
        return jsonify({
            "error": "Password is required"
        }), 400

    if role not in ["parent", "lsa"]:
        return jsonify({
            "error": "Invalid role"
        }), 400

    existing_user = User.query.filter_by(
        email=email
    ).first()

    if existing_user:
        return jsonify({
            "error": "Email already registered"
        }), 409

    user = User(
        email=email,
        role=role,
        is_active=True,
    )

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }), 201
