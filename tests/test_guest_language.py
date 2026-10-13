"""게스트 퍼즐 언어 선호 — 생성 시 지정, PATCH /me 로 변경, /me/stats 에 노출."""

from app.extensions import db
from app.models import Guest, PuzzleLanguage


def _guest_of(headers) -> Guest:
    token = headers["Authorization"].removeprefix("Bearer ")
    return Guest.query.filter_by(token=token).one()


def test_guest_defaults_to_korean_when_language_is_omitted(client):
    res = client.post("/api/v1/guests")

    assert res.status_code == 201
    guest = Guest.query.filter_by(token=res.get_json()["token"]).one()
    assert guest.puzzle_language == PuzzleLanguage.KO


def test_guest_can_be_created_with_english_preference(client):
    res = client.post("/api/v1/guests", json={"puzzle_language": "en"})

    assert res.status_code == 201
    guest = Guest.query.filter_by(token=res.get_json()["token"]).one()
    assert guest.puzzle_language == PuzzleLanguage.EN


def test_unsupported_language_on_create_is_a_validation_error(client):
    res = client.post("/api/v1/guests", json={"puzzle_language": "jp"})

    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"
    assert Guest.query.count() == 0


def test_patch_me_changes_puzzle_language(client, guest_headers):
    res = client.patch("/api/v1/me", headers=guest_headers, json={"puzzle_language": "en"})

    assert res.status_code == 200
    assert res.get_json() == {"puzzle_language": "en"}

    db.session.expire_all()
    assert _guest_of(guest_headers).puzzle_language == PuzzleLanguage.EN


def test_patch_me_rejects_unsupported_language_and_keeps_current(client, guest_headers):
    res = client.patch("/api/v1/me", headers=guest_headers, json={"puzzle_language": "jp"})

    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"

    db.session.expire_all()
    assert _guest_of(guest_headers).puzzle_language == PuzzleLanguage.KO


def test_patch_me_requires_auth(client):
    res = client.patch("/api/v1/me", json={"puzzle_language": "en"})

    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"


def test_me_stats_includes_puzzle_language(client, guest_headers):
    assert client.get("/api/v1/me/stats", headers=guest_headers).get_json()["puzzle_language"] == (
        "ko"
    )

    client.patch("/api/v1/me", headers=guest_headers, json={"puzzle_language": "en"})

    res = client.get("/api/v1/me/stats", headers=guest_headers)
    assert res.get_json()["puzzle_language"] == "en"
