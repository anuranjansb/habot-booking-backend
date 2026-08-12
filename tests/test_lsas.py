from datetime import datetime, timezone

from app.extensions import db
from app.models import LSAProfile


def create_lsa_data(app):
    with app.app_context():
        active_lsa = LSAProfile(
            name="Active LSA",
            email="active@test.com",
            skills=["ADHD", "Dyslexia"],
            is_active=True,
        )

        inactive_lsa = LSAProfile(
            name="Inactive LSA",
            email="inactive@test.com",
            skills=["ADHD"],
            is_active=False,
        )

        other_skill_lsa = LSAProfile(
            name="Other Skill LSA",
            email="other@test.com",
            skills=["Autism"],
            is_active=True,
        )

        db.session.add_all([
            active_lsa,
            inactive_lsa,
            other_skill_lsa,
        ])

        db.session.commit()


def create_parent(app):
    from app.models import Parent

    parent = Parent(
        name="Test Parent",
        email="parent-lsa-test@test.com",
    )

    db.session.add(parent)
    db.session.commit()

    return parent.id


def test_search_lsa_by_skill(client, app, auth_headers):
    create_lsa_data(app)

    response = client.get(
        "/api/v1/lsas/search/?skill=ADHD",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json

    assert len(data) == 1
    assert data[0]["name"] == "Active LSA"
    assert "ADHD" in data[0]["skills"]


def test_inactive_lsa_not_returned(client, app, auth_headers):
    create_lsa_data(app)

    response = client.get(
        "/api/v1/lsas/search/",
        headers=auth_headers,
    )

    assert response.status_code == 200

    names = [lsa["name"] for lsa in response.json]

    assert "Active LSA" in names
    assert "Inactive LSA" not in names


def test_unavailable_lsa_not_returned(
    client,
    app,
    auth_headers,
):
    create_lsa_data(app)

    with app.app_context():
        lsa = LSAProfile.query.filter_by(
            email="active@test.com"
        ).first()

        parent_id = create_parent(app)

        from app.models import BookingRequest, BookingStatus

        booking = BookingRequest(
            parent_id=parent_id,
            lsa_id=lsa.id,
            start_time=datetime(
                2026,
                8,
                15,
                10,
                0,
                tzinfo=timezone.utc,
            ),
            end_time=datetime(
                2026,
                8,
                15,
                11,
                0,
                tzinfo=timezone.utc,
            ),
            status=BookingStatus.CONFIRMED,
        )

        db.session.add(booking)
        db.session.commit()

    response = client.get(
        "/api/v1/lsas/search/"
        "?skill=ADHD"
        "&start_time=2026-08-15T10:30:00Z"
        "&end_time=2026-08-15T11:30:00Z",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json == []


def test_create_booking_inactive_lsa(
    client,
    app,
    auth_user,
):
    from app.extensions import db
    from app.models import LSAProfile

    parent_id = auth_user["parent_id"]
    headers = auth_user["headers"]

    with app.app_context():
        lsa = LSAProfile(
            name="Inactive LSA",
            email="inactive-lsa@test.com",
            skills=["ADHD"],
            is_active=False,
        )

        db.session.add(lsa)
        db.session.commit()

        lsa_id = lsa.id

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == "LSA is not active"


def test_search_lsas_requires_auth(client):
    response = client.get(
        "/api/v1/lsas/search/"
    )

    assert response.status_code == 401


def test_lsa_role_cannot_search_lsas(client, app):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(
            identity="999",
            additional_claims={
                "role": "lsa",
            },
        )

    response = client.get(
        "/api/v1/lsas/search/",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403
    assert response.json["error"] == "Forbidden"


def test_lsa_role_cannot_create_booking(client, app):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(
            identity="999",
            additional_claims={
                "role": "lsa",
            },
        )

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": 1,
            "lsa_id": 1,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403
    assert response.json["error"] == "Forbidden"


def test_search_lsa_empty_skill(client):
    response = client.get(
        "/api/v1/lsas/search/?skill="
    )

    assert response.status_code == 400
    assert response.json["error"] == "skill must not be empty"


def test_search_lsa_empty_skill(client, auth_headers):
    response = client.get(
        "/api/v1/lsas/search/?skill=",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == "skill must not be empty"


def test_search_lsa_whitespace_skill(client, auth_headers):
    response = client.get(
        "/api/v1/lsas/search/?skill=%20%20%20",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == "skill must not be empty"


def test_search_lsa_missing_end_time(client, auth_headers):
    response = client.get(
        "/api/v1/lsas/search/"
        "?start_time=2026-08-15T10:00:00Z",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "start_time and end_time must be provided together"
    )


def test_search_lsa_missing_start_time(client, auth_headers):
    response = client.get(
        "/api/v1/lsas/search/"
        "?end_time=2026-08-15T11:00:00Z",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "start_time and end_time must be provided together"
    )


def test_search_lsa_invalid_datetime(client, auth_headers):
    response = client.get(
        "/api/v1/lsas/search/"
        "?start_time=invalid"
        "&end_time=2026-08-15T11:00:00Z",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == "Invalid datetime format"


def test_search_lsa_without_timezone(client, auth_headers):
    response = client.get(
        "/api/v1/lsas/search/"
        "?start_time=2026-08-15T10:00:00"
        "&end_time=2026-08-15T11:00:00",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "Datetime must include timezone information"
    )


def test_search_lsa_end_before_start(client, auth_headers):
    response = client.get(
        "/api/v1/lsas/search/"
        "?start_time=2026-08-15T11:00:00Z"
        "&end_time=2026-08-15T10:00:00Z",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json["error"] == (
        "end_time must be after start_time"
    )
