from app.extensions import db
from app.auth import role_required
from flask import Flask
import pytest
from flask_jwt_extended import create_access_token


def test_register_parent(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "parent@example.com",
            "password": "securepassword123",
            "role": "parent",
        },
    )

    assert response.status_code == 201

    data = response.json

    assert data["email"] == "parent@example.com"
    assert data["role"] == "parent"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


def test_register_lsa(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "lsa@example.com",
            "password": "securepassword123",
            "role": "lsa",
        },
    )

    assert response.status_code == 201
    assert response.json["role"] == "lsa"


def test_register_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "securepassword123",
        "role": "parent",
    }

    first_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert second_response.status_code == 409
    assert second_response.json["error"] == (
        "Email already registered"
    )


def test_register_invalid_role(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid@example.com",
            "password": "securepassword123",
            "role": "admin",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "Invalid role"


def test_register_missing_fields(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "parent@example.com",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "Missing required fields"


def test_login_success(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "securepassword123",
            "role": "parent",
        },
    )

    assert register_response.status_code == 201

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "securepassword123",
        },
    )

    assert response.status_code == 200

    data = response.json

    assert "access_token" in data
    assert data["token_type"] == "Bearer"


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong-password@example.com",
            "password": "securepassword123",
            "role": "parent",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert response.json["error"] == "Invalid email or password"


def test_login_unknown_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "does-not-exist@example.com",
            "password": "securepassword123",
        },
    )

    assert response.status_code == 401
    assert response.json["error"] == "Invalid email or password"


def test_login_missing_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Email and password are required"
    )


def test_login_inactive_user(client, app):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        user = User(
            email="inactive@example.com",
            role="parent",
            is_active=False,
        )
        user.set_password("securepassword123")

        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "securepassword123",
        },
    )

    assert response.status_code == 403
    assert response.json["error"] == "User account is inactive"


def make_token(app, role):
    with app.app_context():
        token = create_access_token(
            identity="1",
            additional_claims={
                "role": role,
            },
        )

    return {
        "Authorization": f"Bearer {token}",
    }


def test_parent_role_allowed(app):
    app.config["TESTING"] = True

    with app.test_request_context():
        pass
