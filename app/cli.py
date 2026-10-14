import click
from flask.cli import with_appcontext

from app.models import PuzzleLanguage
from app.services.access_log_service import monthly_report, verify_chain
from app.services.book_lookup_service import search_books
from app.services.operator_alert_service import notify_operator
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
@click.option(
    "--language",
    default=PuzzleLanguage.KO.value,
    show_default=True,
    type=click.Choice([language.value for language in PuzzleLanguage]),
    help="배정할 퍼즐 언어 (언어마다 따로 돌린다)",
)
@click.option("--days", default=30, show_default=True, type=int, help="배정할 일 수")
@click.option(
    "--avoid-days",
    default=14,
    show_default=True,
    type=int,
    help="최근 며칠 안에 배정된 단어는 피한다 (단어 풀이 작으면 자동으로 완화됨)",
)
@with_appcontext
def schedule_puzzles_command(language, days, avoid_days):
    created = schedule_puzzles(
        PuzzleLanguage(language), days=days, avoid_days=avoid_days
    )
    click.echo(f"{language} {created}일치 퍼즐 배정 완료 (이미 있던 날짜는 건너뜀)")


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
        word, created = add_word_from_book(results[add_index])
        if created:
            click.echo(f"등록 완료: {word.answer} (chosung={word.chosung})")
        else:
            click.echo(f"이미 등록돼 있음: {word.answer} (chosung={word.chosung})")


@click.command("notify-operator-test")
@with_appcontext
def notify_operator_test_command():
    """운영자 Slack 알림이 실제로 도착하는지 한 번 확인한다.

    Webhook URL 은 운영자가 .env 에 넣는 값이라, 코드가 아니라 이 명령으로
    "채널에 뜨는지" 를 확인하는 게 유일한 검증 수단이다.
    """
    if notify_operator("연결 테스트", "운영자 알림 경로가 살아 있습니다."):
        click.echo("전송 완료 — Slack 채널을 확인하세요")
    else:
        click.echo("전송하지 않음 — SLACK_WEBHOOK_URL 설정과 서버 로그를 확인하세요")


@click.group("access-log")
def access_log_group():
    """개인정보처리시스템 접속기록의 점검 명령(고시 제8조).

    기록은 요청 경로가 자동으로 남긴다(`app/access_log.py`) — 여기 있는 건 사람이
    "손대진 않았나"(verify)와 "이번 달에 무슨 일이 있었나"(report)를 확인하는 쪽이다.
    월 1회 점검 절차는 `docs/RELEASE.md` "### 36.".
    """


@access_log_group.command("verify")
@with_appcontext
def access_log_verify_command():
    """해시 체인을 처음부터 다시 계산해 끊긴 지점을 찾는다.

    끊긴 게 있으면 **종료 코드가 0 이 아니다** — 사람이 눈으로 보는 것 말고
    점검 스크립트에서도 쓸 수 있어야 한다.
    """
    result = verify_chain()
    if result.broken_at is None:
        click.echo(f"접속기록 {result.checked}행 검증 — 이상 없음")
        return
    click.echo(f"접속기록 체인이 끊겼습니다: id={result.broken_at} ({result.checked}행까지 검증)")
    raise SystemExit(1)


@access_log_group.command("report")
@click.option("--month", required=True, help="점검할 달 (YYYY-MM)")
@with_appcontext
def access_log_report_command(month):
    """월별 행위 수·거부 수·체인 검증 결과. 고시 제8조 제2항의 월 1회 점검용."""
    try:
        report = monthly_report(month)
    except ValueError:
        raise click.BadParameter("YYYY-MM 형식이어야 합니다", param_hint="--month") from None

    click.echo(f"[{report.month}] 접속기록 총 {report.total}건, 거부 {report.denied}건")
    for action, count in sorted(report.by_action.items(), key=lambda item: (-item[1], item[0])):
        click.echo(f"  {action} {count}")
    if report.chain.broken_at is None:
        click.echo(f"체인 검증({report.chain.checked}행) — 이상 없음")
    else:
        click.echo(f"체인 검증 — 끊긴 지점 id={report.chain.broken_at}")


def register_commands(app):
    app.cli.add_command(seed_words_command)
    app.cli.add_command(schedule_puzzles_command)
    app.cli.add_command(search_books_command)
    app.cli.add_command(notify_operator_test_command)
    app.cli.add_command(access_log_group)
