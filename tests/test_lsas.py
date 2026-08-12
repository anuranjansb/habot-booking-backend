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


def test_search_lsa_by_skill(client, app):
    create_lsa_data(app)

    response = client.get(
        "/api/v1/lsas/search/?skill=ADHD"
    )

    assert response.status_code == 200

    data = response.json

    assert len(data) == 1
    assert data[0]["name"] == "Active LSA"
    assert "ADHD" in data[0]["skills"]


def test_inactive_lsa_not_returned(client, app):
    create_lsa_data(app)

    response = client.get(
        "/api/v1/lsas/search/"
    )

    assert response.status_code == 200

    names = [lsa["name"] for lsa in response.json]

    assert "Active LSA" in names
    assert "Inactive LSA" not in names


def test_unavailable_lsa_not_returned(client, app):
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
        "&end_time=2026-08-15T11:30:00Z"
    )

    assert response.status_code == 200
    assert response.json == []


def test_create_booking_inactive_lsa(client, app):
    from app.extensions import db
    from app.models import LSAProfile, Parent

    with app.app_context():
        parent = Parent(
            name="Test Parent",
            email="parent@test.com",
        )

        lsa = LSAProfile(
            name="Inactive LSA",
            email="inactive@test.com",
            skills=["ADHD"],
            is_active=False,
        )

        db.session.add(parent)
        db.session.add(lsa)
        db.session.commit()

        parent_id = parent.id
        lsa_id = lsa.id

    response = client.post(
        "/api/v1/bookings/",
        json={
            "parent_id": parent_id,
            "lsa_id": lsa_id,
            "start_time": "2026-08-15T10:00:00+00:00",
            "end_time": "2026-08-15T11:00:00+00:00",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "LSA is not active"
