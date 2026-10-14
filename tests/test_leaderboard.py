import re

from app.services.guest_service import issue_guest
from app.services.puzzle_metrics import anon_tag


def _guess(client, token, puzzle, text):
    return client.post(
        "/api/v1/puzzles/today/guesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"puzzle_id": puzzle.id, "guess": text},
    )


def test_leaderboard_ranks_fewer_attempts_first(client, today_puzzle):
    fast = issue_guest()
    _guess(client, fast.token, today_puzzle, "사과")  # 1번째 시도에 정답

    slow = issue_guest()
    _guess(client, slow.token, today_puzzle, "바바")
    _guess(client, slow.token, today_puzzle, "사과")  # 2번째 시도에 정답

    res = client.get(
        "/api/v1/puzzles/today/leaderboard",
        headers={"Authorization": f"Bearer {fast.token}"},
    )
    body = res.get_json()

    assert res.status_code == 200
    tags = [e["anon_tag"] for e in body["entries"]]
    assert tags == [anon_tag(fast.id), anon_tag(slow.id)]
    assert body["entries"][0]["attempts"] == 1
    assert body["entries"][0]["is_me"] is True
    assert body["entries"][1]["attempts"] == 2
    assert body["entries"][1]["is_me"] is False


def test_leaderboard_respects_limit(client, today_puzzle):
    for _ in range(3):
        guest = issue_guest()
        _guess(client, guest.token, today_puzzle, "사과")

    res = client.get(
        "/api/v1/puzzles/today/leaderboard?limit=2",
        headers={"Authorization": f"Bearer {guest.token}"},
    )
    body = res.get_json()

    assert len(body["entries"]) == 2
    assert [e["rank"] for e in body["entries"]] == [1, 2]


def test_leaderboard_entries_do_not_leak_guest_id(client, today_puzzle):
    guest = issue_guest()
    _guess(client, guest.token, today_puzzle, "사과")

    body = client.get(
        "/api/v1/puzzles/today/leaderboard",
        headers={"Authorization": f"Bearer {guest.token}"},
    ).get_json()

    entry = body["entries"][0]
    assert set(entry) == {"rank", "anon_tag", "attempts", "seconds", "is_me"}
    assert entry["anon_tag"] == anon_tag(guest.id)


def test_anon_tag_is_guest_id_in_four_hex_digits():
    assert anon_tag(1) == "0001"
    assert anon_tag(0xA3F1) == "a3f1"
    # 0x10000 로 나눈 나머지만 쓰기 때문에 65536번째 게스트부터 태그가 겹친다
    # (식별용이 아니라 표시용이라 충돌을 허용한다).
    assert anon_tag(0x10001) == anon_tag(1)


def test_the_leaderboard_response_carries_no_ui_language(client, today_puzzle):
    """티켓 38: 서버는 '게스트/Guest' 접두사를 붙이지 않는다 — 붙이는 건 웹·앱이다.

    영어 UI·영문 스토어 스크린샷에 한글 '게스트' 가 보이던 결함이라, 응답 **전체**
    에 한글이 없는지 본다. 필드 하나만 보면 다음에 라벨을 또 서버에서 만들 때
    같은 결함이 조용히 돌아온다.
    """
    guest = issue_guest()
    _guess(client, guest.token, today_puzzle, "사과")

    raw = client.get(
        "/api/v1/puzzles/today/leaderboard",
        headers={"Authorization": f"Bearer {guest.token}"},
    ).get_data(as_text=True)

    assert not re.search(r"[가-힣]", raw), raw


def test_my_rank_comes_down_even_when_outside_the_page(client, today_puzzle):
    """25명 중 23위인 내가 20개짜리 페이지 밖이어도 me.rank 로 내 위치를 안다."""
    guests = [issue_guest() for _ in range(25)]
    # 시도 횟수가 점수의 상위 자리라서, 앞 22명을 1회 정답으로 깔면 2회 정답인
    # 23번째 사람이 정확히 23위가 된다.
    for guest in guests[:22]:
        _guess(client, guest.token, today_puzzle, "사과")

    me = guests[22]
    _guess(client, me.token, today_puzzle, "바바")
    _guess(client, me.token, today_puzzle, "사과")

    for guest in guests[23:]:
        _guess(client, guest.token, today_puzzle, "바바")
        _guess(client, guest.token, today_puzzle, "포도")
        _guess(client, guest.token, today_puzzle, "사과")

    body = client.get(
        "/api/v1/puzzles/today/leaderboard",
        headers={"Authorization": f"Bearer {me.token}"},
    ).get_json()

    assert len(body["entries"]) == 20
    assert all(e["is_me"] is False for e in body["entries"])
    assert body["me"]["rank"] == 23
    assert body["me"]["attempts"] == 2


def test_me_is_null_when_i_have_not_solved_today(client, today_puzzle):
    solver = issue_guest()
    _guess(client, solver.token, today_puzzle, "사과")

    watcher = issue_guest()
    body = client.get(
        "/api/v1/puzzles/today/leaderboard",
        headers={"Authorization": f"Bearer {watcher.token}"},
    ).get_json()

    assert len(body["entries"]) == 1
    assert body["me"] is None


def test_me_is_filled_even_when_i_am_on_the_page(client, today_puzzle):
    guest = issue_guest()
    _guess(client, guest.token, today_puzzle, "사과")

    body = client.get(
        "/api/v1/puzzles/today/leaderboard",
        headers={"Authorization": f"Bearer {guest.token}"},
    ).get_json()

    assert body["entries"][0]["is_me"] is True
    assert body["me"] == {
        "rank": 1,
        "attempts": 1,
        "seconds": body["entries"][0]["seconds"],
    }
