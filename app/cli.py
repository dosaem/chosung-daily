import click
from flask.cli import with_appcontext

from app.services.book_lookup_service import search_books
from app.services.puzzle_schedule_service import schedule_puzzles
from app.services.word_service import add_word_from_book, seed_words_from_csv


@click.command("seed-words")
@click.argument("csv_path")
@with_appcontext
def seed_words_command(csv_path):
    result = seed_words_from_csv(csv_path)
    for line in result.skipped:
        click.echo(f"건너뜀: {line}")
    click.echo(f"{result.created}개 단어 시드 완료")


@click.command("schedule-puzzles")
@click.option("--days", default=30, show_default=True, type=int, help="배정할 일 수")
@click.option(
    "--avoid-days",
    default=14,
    show_default=True,
    type=int,
    help="최근 며칠 안에 배정된 단어는 피한다 (단어 풀이 작으면 자동으로 완화됨)",
)
@with_appcontext
def schedule_puzzles_command(days, avoid_days):
    created = schedule_puzzles(days=days, avoid_days=avoid_days)
    click.echo(f"{created}일치 퍼즐 배정 완료 (이미 있던 날짜는 건너뜀)")


@click.command("search-books")
@click.argument("query")
@click.option("--size", default=5, show_default=True, type=int)
@click.option(
    "--add",
    "add_index",
    type=int,
    default=None,
    help="검색 결과 중 N번째를 book_title Word로 바로 등록",
)
@with_appcontext
def search_books_command(query, size, add_index):
    """카카오/알라딘 책 검색 API로 책 정보를 찾아서 book_title 단어로 등록한다.

    운영용 CLI다 — 플레이어가 쓰는 기능이 아니라, 관리자가 실제 존재하는 책
    제목을 단어 풀에 넣을 때 쓴다. KAKAO_REST_API_KEY / ALADIN_TTB_KEY 둘 다
    설정 안 돼 있으면 결과가 비어서 나온다.
    """
    results = search_books(query, size=size)
    if not results:
        click.echo(
            "검색 결과 없음 (API 키가 안 설정됐을 수 있음 — "
            ".env의 KAKAO_REST_API_KEY / ALADIN_TTB_KEY 확인)"
        )
        return

    for i, book in enumerate(results):
        author = book.author or "저자 미상"
        publisher = book.publisher or ""
        click.echo(f"[{i}] ({book.source}) {book.title} - {author} / {publisher}")

    if add_index is not None:
        if not (0 <= add_index < len(results)):
            click.echo(f"--add 값이 범위를 벗어남 (0~{len(results) - 1})")
            return
        word = add_word_from_book(results[add_index])
        click.echo(f"등록 완료: {word.answer} (chosung={word.chosung})")


def register_commands(app):
    app.cli.add_command(seed_words_command)
    app.cli.add_command(schedule_puzzles_command)
    app.cli.add_command(search_books_command)
