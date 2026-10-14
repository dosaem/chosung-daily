"""CSV 업로드 — 헤더 검증, UTF-8 BOM, 행별 결과(추가/중복/오류+사유) 표."""

import io
import re

from app.extensions import db
from app.models import PuzzleLanguage, Word, WordCategory

HEADER = "language,category,answer,hint"
CSRF_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')


def _token(client):
    html = client.get("/admin/words/import").get_data(as_text=True)
    return CSRF_PATTERN.search(html).group(1)


def _upload(client, body: bytes | str, filename="words.csv"):
    data = body.encode("utf-8") if isinstance(body, str) else body
    return client.post(
        "/admin/words/import",
        data={
            "csrf_token": _token(client),
            "file": (io.BytesIO(data), filename),
        },
        content_type="multipart/form-data",
    )


def test_upload_adds_rows_and_shows_the_result_table(admin_session):
    res = _upload(
        admin_session,
        f"{HEADER}\nko,general,지하철역,타는 곳\nen,general,apple,red fruit\n",
    )
    html = res.get_data(as_text=True)

    assert res.status_code == 200
    assert Word.query.count() == 2
    assert html.count("추가") >= 2
    assert "지하철역" in html
    assert "apple" in html


def test_upload_accepts_a_utf8_bom(admin_session):
    """엑셀이 저장한 CSV 는 BOM 으로 시작한다 — 그러면 첫 헤더 이름이 안 맞는다."""
    body = f"{HEADER}\nko,general,사과,과일\n".encode("utf-8-sig")

    res = _upload(admin_session, body)

    assert res.status_code == 200
    assert Word.query.count() == 1


def test_upload_marks_duplicates_without_adding_them(admin_session):
    db.session.add(
        Word(answer="사과", language=PuzzleLanguage.KO, category=WordCategory.GENERAL, hint="과일")
    )
    db.session.commit()

    res = _upload(admin_session, f"{HEADER}\nko,general,사과,다른 힌트\n")
    html = res.get_data(as_text=True)

    assert "중복" in html
    assert Word.query.count() == 1


def test_upload_marks_a_row_repeated_inside_the_same_file_as_duplicate(admin_session):
    res = _upload(admin_session, f"{HEADER}\nko,general,사과,과일\nko,general,사과,과일\n")
    html = res.get_data(as_text=True)

    assert Word.query.count() == 1
    assert "중복" in html


def test_upload_shows_the_reason_of_a_broken_row_and_keeps_the_good_ones(admin_session):
    res = _upload(
        admin_session,
        f"{HEADER}\nko,general,사과,과일\nfr,general,pomme,fruit\nko,없는카테고리,학교,배우는 곳\n",
    )
    html = res.get_data(as_text=True)

    assert Word.query.count() == 1
    assert "오류" in html
    assert "language" in html
    assert "category" in html


def test_upload_rejects_a_header_that_lacks_a_column(admin_session):
    res = _upload(admin_session, "answer,hint\n사과,과일\n")
    html = res.get_data(as_text=True)

    assert res.status_code == 200
    assert "language" in html
    assert "category" in html
    assert Word.query.count() == 0


def test_upload_rejects_a_file_that_is_not_utf8(admin_session):
    res = _upload(admin_session, f"{HEADER}\nko,general,사과,과일\n".encode("cp949"))

    assert res.status_code == 200
    assert "UTF-8" in res.get_data(as_text=True)
    assert Word.query.count() == 0


def test_upload_without_a_file_shows_a_message(admin_session):
    res = admin_session.post(
        "/admin/words/import",
        data={"csrf_token": _token(admin_session)},
        content_type="multipart/form-data",
    )

    assert res.status_code == 200
    assert "CSV" in res.get_data(as_text=True)


def test_upload_without_a_csrf_token_is_forbidden(admin_session):
    res = admin_session.post(
        "/admin/words/import",
        data={"file": (io.BytesIO(f"{HEADER}\nko,general,사과,과일\n".encode()), "w.csv")},
        content_type="multipart/form-data",
    )

    assert res.status_code == 403
    assert Word.query.count() == 0
