from app.extensions import db
from app.models import Guest, GuestStats


def test_create_guest_issues_token(client, app):
    res = client.post("/api/v1/guests")

    assert res.status_code == 201
    token = res.get_json()["token"]
    assert token

    assert Guest.query.filter_by(token=token).count() == 1


def test_create_guest_also_creates_stats_row(client, app):
    res = client.post("/api/v1/guests")
    token = res.get_json()["token"]

    guest = Guest.query.filter_by(token=token).one()
    stats = db.session.get(GuestStats, guest.id)
    assert stats is not None
    assert stats.current_streak == 0
