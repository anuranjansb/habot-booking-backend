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
