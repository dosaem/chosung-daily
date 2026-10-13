from app.extensions import db
from app.models import Guest, GuestStats, PuzzleLanguage
from app.repositories.guest_repository import find_by_token


def issue_guest(puzzle_language: PuzzleLanguage = PuzzleLanguage.KO) -> Guest:
    """게스트 토큰을 발급한다. GuestStats를 같은 트랜잭션에서 같이 만들어서,
    이후 코드가 "게스트가 있으면 stats도 항상 있다"는 전제를 믿고 쓸 수 있게 한다.

    퍼즐 언어는 생성 시점에 정해지고(기본 ko) 이후 `change_puzzle_language`로 바뀐다.
    """
    guest = Guest(puzzle_language=puzzle_language)
    db.session.add(guest)
    db.session.flush()  # GuestStats.guest_id FK를 쓰려면 guest.id가 먼저 필요

    db.session.add(GuestStats(guest_id=guest.id))
    db.session.commit()
    return guest


def change_puzzle_language(guest: Guest, puzzle_language: PuzzleLanguage) -> Guest:
    """게스트의 퍼즐 언어 선호를 바꾼다.

    진행 중인 시도 기록은 퍼즐(언어)에 묶여 있어서 건드리지 않는다 — 언어를 되돌리면
    그 언어의 보드가 그대로 돌아온다.
    """
    guest.puzzle_language = puzzle_language
    db.session.commit()
    return guest


def get_guest_by_token(token: str) -> Guest | None:
    return find_by_token(token)
