from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt


def role_required(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()

            user_role = claims.get("role")

            if user_role != required_role:
                return jsonify({
                    "error": "Forbidden",
                    "message": (
                        f"{required_role} role required"
                    ),
                }), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator
