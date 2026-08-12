from app.errors import APIError
from datetime import timedelta

from flask_jwt_extended import create_access_token


def test_api_error_handler(client):
    @client.application.route("/test-api-error")
    def test_error():
        raise APIError(
            "Something went wrong",
            400,
            "Test error",
        )

    response = client.get("/test-api-error")

    assert response.status_code == 400
    assert response.json == {
        "error": "Test error",
        "message": "Something went wrong",
    }


def test_unexpected_error_handler(client):
    @client.application.route("/test-unexpected-error")
    def test_error():
        raise RuntimeError("secret internal error")

    response = client.get("/test-unexpected-error")

    assert response.status_code == 500

    assert response.json == {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
    }


def test_404_returns_json(client):
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404
    assert response.json["error"] == "Not Found"
    assert "message" in response.json


def test_405_returns_json(client):
    response = client.post("/api/v1/lsas/search/")

    assert response.status_code == 405
    assert response.json["error"] == "Method Not Allowed"
    assert "message" in response.json


def test_missing_jwt_returns_json(client):
    response = client.get("/api/v1/bookings/1")

    assert response.status_code == 401

    assert response.json == {
        "error": "Unauthorized",
        "message": "Authentication token is required",
    }


def test_invalid_jwt_returns_json(client):
    response = client.get(
        "/api/v1/bookings/1",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401

    assert response.json == {
        "error": "Unauthorized",
        "message": "Invalid authentication token",
    }


def test_expired_jwt_returns_json(client, app):
    with app.app_context():
        token = create_access_token(
            identity="1",
            expires_delta=timedelta(seconds=-1),
            additional_claims={
                "role": "parent",
            },
        )

    response = client.get(
        "/api/v1/bookings/1",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401

    assert response.json == {
        "error": "Unauthorized",
        "message": "Authentication token has expired",
    }
