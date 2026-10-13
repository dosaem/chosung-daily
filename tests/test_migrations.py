"""Alembic 마이그레이션 왕복 테스트 — upgrade → 데이터 → downgrade → upgrade.

다른 테스트는 `conftest.py`의 `db.create_all()`로 스키마를 만든다. 그 경로는
모델 정의만 보기 때문에 마이그레이션 파일이 실제로 돌아가는지, 되돌릴 수 있는지,
기존 데이터가 보존되는지는 하나도 검증하지 못한다. 그래서 이 테스트는
**별도 DB + `flask db` 서브프로세스**로 운영 배포와 같은 경로를 밟는다.

쓰는 DB는 `TEST_MIGRATION_DATABASE_URL`(없으면 테스트 DB 이름 + `_migrations`)
이고, 테이블을 전부 지우고 시작한다 — 다른 테스트의 DB는 건드리지 않는다.
DB 를 만드는 방법은 README "실행 방법"에 있다.
"""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.config import TestingConfig
from app.models.enums import PuzzleLanguage
from app.utils.chosung import extract_chosung
from app.utils.mask import build_mask

REPO_ROOT = Path(__file__).resolve().parent.parent

PREVIOUS_REVISION = "9ec267465b4e"  # 퍼즐 언어 직전 리비전
LANGUAGE_REVISION = "4e72a4045fbc"  # 퍼즐 언어 = 설정 테이블 직전 리비전

PUZZLE_DATE = date(2026, 10, 13)
KO_ANSWER = "해리 포터"
GUEST_TOKEN = "migration-round-trip-guest"


def _migration_database_url() -> str:
    override = os.environ.get("TEST_MIGRATION_DATABASE_URL")
    if override:
        return override

    url = make_url(TestingConfig.SQLALCHEMY_DATABASE_URI)
    return url.set(database=f"{url.database}_migrations").render_as_string(hide_password=False)


def _run_flask_db(database_url: str, *args: str) -> None:
    """`flask db ...`를 서브프로세스로 돌린다 — 배포가 쓰는 그 명령 그대로."""
    env = {
        **os.environ,
        "FLASK_APP": "wsgi.py",
        "FLASK_ENV": "development",
        "DATABASE_URL": database_url,
    }
    completed = subprocess.run(
        [sys.executable, "-m", "flask", "db", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"flask db {' '.join(args)} 실패\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )


def _drop_every_table(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for (table,) in conn.execute(text("SHOW TABLES")).all():
            conn.execute(text(f"DROP TABLE `{table}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture
def migration_engine():
    database_url = _migration_database_url()
    engine = create_engine(database_url)

    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        pytest.fail(
            f"마이그레이션 왕복 테스트용 DB에 접속할 수 없다: {make_url(database_url).database}\n"
            "README '실행 방법'의 CREATE DATABASE 안내를 따라 만들어라.\n"
            f"({exc.__class__.__name__})"
        )

    _drop_every_table(engine)
    yield engine
    _drop_every_table(engine)
    engine.dispose()


def _table_names(engine) -> set[str]:
    with engine.connect() as conn:
        return {row[0] for row in conn.execute(text("SHOW TABLES")).all()}


def _insert_korean_data(engine) -> None:
    """마이그레이션 직후(=언어가 들어온 뒤)의 ko 데이터를 ORM 없이 넣는다.

    모델·이벤트 리스너를 거치지 않는 게 핵심이다 — 마이그레이션이 만든 스키마만
    가지고 쓸 수 있어야 한다.
    """
    mask = json.dumps(build_mask(PuzzleLanguage.KO, KO_ANSWER), ensure_ascii=False)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO word (answer, language, mask, chosung, category, hint, created_at) "
                "VALUES (:answer, 'ko', :mask, :chosung, 'book_title', :hint, NOW())"
            ),
            {
                "answer": KO_ANSWER,
                "mask": mask,
                "chosung": extract_chosung(KO_ANSWER),
                "hint": "조앤 K. 롤링",
            },
        )
        conn.execute(
            text(
                "INSERT INTO guest (token, puzzle_language, created_at) "
                "VALUES (:token, 'ko', NOW())"
            ),
            {"token": GUEST_TOKEN},
        )
        conn.execute(
            text(
                "INSERT INTO daily_puzzle (puzzle_date, language, word_id, created_at) "
                "SELECT :puzzle_date, 'ko', id, NOW() FROM word"
            ),
            {"puzzle_date": PUZZLE_DATE},
        )
        conn.execute(
            text(
                "INSERT INTO attempt "
                "(guest_id, puzzle_id, guess, is_correct, attempt_no, created_at) "
                "SELECT g.id, p.id, :guess, 1, 1, NOW() FROM guest g, daily_puzzle p"
            ),
            {"guess": KO_ANSWER},
        )
        conn.execute(
            text(
                "INSERT INTO daily_stats (puzzle_date, language, distribution, solver_count) "
                "VALUES (:puzzle_date, 'ko', :distribution, 1)"
            ),
            {"puzzle_date": PUZZLE_DATE, "distribution": json.dumps({"1": 1})},
        )


def _snapshot(engine) -> dict:
    with engine.connect() as conn:
        word = conn.execute(
            text("SELECT id, answer, language, mask, chosung, category, hint FROM word")
        ).mappings().one()
        puzzle = conn.execute(
            text("SELECT puzzle_date, language, word_id FROM daily_puzzle")
        ).mappings().one()
        attempt = conn.execute(
            text("SELECT guest_id, puzzle_id, guess, is_correct, attempt_no FROM attempt")
        ).mappings().one()
        guest = conn.execute(
            text("SELECT token, puzzle_language FROM guest")
        ).mappings().one()
        stats = conn.execute(
            text("SELECT puzzle_date, language, solver_count FROM daily_stats")
        ).mappings().one()

    return {
        "word": dict(word) | {"mask": json.loads(word["mask"])},
        "puzzle": dict(puzzle),
        "attempt": dict(attempt),
        "guest": dict(guest),
        "stats": dict(stats),
    }


def test_korean_data_survives_downgrade_and_upgrade(migration_engine):
    _run_flask_db(_migration_database_url(), "upgrade")
    _insert_korean_data(migration_engine)
    before = _snapshot(migration_engine)

    _run_flask_db(_migration_database_url(), "downgrade", PREVIOUS_REVISION)
    _run_flask_db(_migration_database_url(), "upgrade")

    after = _snapshot(migration_engine)
    assert after == before


def test_downgrade_removes_the_language_columns(migration_engine):
    """되돌리기가 실제로 옛 스키마로 돌아가야(= 왕복이 의미가 있어야) 한다."""
    _run_flask_db(_migration_database_url(), "upgrade")
    _run_flask_db(_migration_database_url(), "downgrade", PREVIOUS_REVISION)

    with migration_engine.connect() as conn:
        word_columns = {
            row[0] for row in conn.execute(text("SHOW COLUMNS FROM word")).all()
        }
        puzzle_indexes = {
            row[2] for row in conn.execute(text("SHOW INDEX FROM daily_puzzle")).all()
        }

    assert "language" not in word_columns
    assert "mask" not in word_columns
    assert "uq_daily_puzzle_date_language" not in puzzle_indexes


def test_upgrade_fills_mask_for_rows_created_before_the_column_existed(migration_engine):
    """옛 스키마 시절 단어(언어·가림 컬럼이 없던 행)도 upgrade 후 가림을 갖는다."""
    _run_flask_db(_migration_database_url(), "upgrade")
    _run_flask_db(_migration_database_url(), "downgrade", PREVIOUS_REVISION)

    with migration_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO word (answer, chosung, category, hint, created_at) "
                "VALUES (:answer, :chosung, 'general', '힌트', NOW())"
            ),
            {"answer": "사과", "chosung": extract_chosung("사과")},
        )

    _run_flask_db(_migration_database_url(), "upgrade")

    with migration_engine.connect() as conn:
        row = conn.execute(text("SELECT language, mask FROM word")).mappings().one()

    assert row["language"] == PuzzleLanguage.KO.value
    assert json.loads(row["mask"]) == build_mask(PuzzleLanguage.KO, "사과")


def test_both_languages_fit_on_the_same_date_after_upgrade(migration_engine):
    _run_flask_db(_migration_database_url(), "upgrade")

    with migration_engine.begin() as conn:
        for language, answer in (("ko", "사과"), ("en", "apple")):
            conn.execute(
                text(
                    "INSERT INTO word "
                    "(answer, language, mask, chosung, category, hint, created_at) "
                    "VALUES (:answer, :language, :mask, :chosung, 'general', '힌트', NOW())"
                ),
                {
                    "answer": answer,
                    "language": language,
                    "mask": json.dumps(build_mask(PuzzleLanguage(language), answer)),
                    "chosung": extract_chosung(answer),
                },
            )
            conn.execute(
                text(
                    "INSERT INTO daily_puzzle (puzzle_date, language, word_id, created_at) "
                    "SELECT :puzzle_date, :language, id, NOW() FROM word WHERE answer = :answer"
                ),
                {"puzzle_date": PUZZLE_DATE, "language": language, "answer": answer},
            )

    with migration_engine.connect() as conn:
        languages = {
            row[0]
            for row in conn.execute(
                text("SELECT language FROM daily_puzzle WHERE puzzle_date = :d"),
                {"d": PUZZLE_DATE},
            ).all()
        }

    assert languages == {"ko", "en"}


def test_app_setting_table_round_trips(migration_engine):
    """08: 설정 테이블이 upgrade 로 생기고 downgrade 로 사라져야 한다."""
    _run_flask_db(_migration_database_url(), "upgrade")
    assert "app_setting" in _table_names(migration_engine)

    _run_flask_db(_migration_database_url(), "downgrade", LANGUAGE_REVISION)
    assert "app_setting" not in _table_names(migration_engine)

    _run_flask_db(_migration_database_url(), "upgrade")
    assert "app_setting" in _table_names(migration_engine)


def test_app_setting_rows_written_without_the_orm_are_readable(migration_engine):
    """마이그레이션이 만든 스키마만으로 설정 행을 쓰고 읽을 수 있어야 한다 —
    운영자가 DB 에 직접 행을 넣는 게 이 테이블의 1차 사용법이다(토글 UI 는 16)."""
    _run_flask_db(_migration_database_url(), "upgrade")

    with migration_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO app_setting (setting_key, value, updated_at) "
                "VALUES ('maintenance_enabled', 'true', NOW())"
            )
        )

    with migration_engine.connect() as conn:
        row = conn.execute(
            text("SELECT setting_key, value FROM app_setting")
        ).mappings().one()

    assert dict(row) == {"setting_key": "maintenance_enabled", "value": "true"}
