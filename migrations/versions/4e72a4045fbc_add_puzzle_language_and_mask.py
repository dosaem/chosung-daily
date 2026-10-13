"""add puzzle language and mask

단어·오늘의 퍼즐·게스트에 퍼즐 언어를 넣고, 가림(mask)을 ko/en 공통 포맷으로
일반화한다. 기존 행은 전부 ko로 남는다.

expand-contract 3단계(새 컬럼 추가 → 양쪽 쓰기 → 옛 컬럼 제거)를 쓰지 않고
마이그레이션 하나 + 코드 변경 하나로 끝낸다 — 트래픽이 운영자 한 명뿐이라
무중단 전환의 값어치보다 3단계를 운영하는 비용이 크다(스펙 §A.1).

`chosung` 컬럼은 지우지 않는다. 기존 클라이언트가 읽는 응답 필드라서, 전부
`mask`로 옮겨간 뒤에 따로 제거한다(스펙 "미정 항목" 10).

데이터 단계에서 기존 단어의 `mask`를 채울 때 `app.utils.mask.build_mask`를
그대로 쓴다 — 가림 규칙을 여기 복사해두면 두 벌이 생기고, 둘이 어긋나면
"저장할 때와 마이그레이션할 때 문제가 다르게 보이는" 버그가 된다.

Revision ID: 4e72a4045fbc
Revises: 9ec267465b4e
Create Date: 2026-10-14 06:27:33.391509

"""
import json

from alembic import op
import sqlalchemy as sa

from app.models.enums import PuzzleLanguage
from app.utils.mask import build_mask


# revision identifiers, used by Alembic.
revision = '4e72a4045fbc'
down_revision = '9ec267465b4e'
branch_labels = None
depends_on = None

PUZZLE_LANGUAGE = sa.Enum('ko', 'en', name='puzzlelanguage')
KO = PuzzleLanguage.KO.value


def upgrade():
    with op.batch_alter_table('word', schema=None) as batch_op:
        batch_op.add_column(sa.Column('language', PUZZLE_LANGUAGE, server_default=KO, nullable=False))
        # MySQL의 JSON 컬럼은 기본값을 가질 수 없어서, 일단 NULL을 허용해 추가하고
        # 아래 데이터 단계에서 채운 뒤 NOT NULL로 조인다.
        batch_op.add_column(sa.Column('mask', sa.JSON(), nullable=True))

    _fill_word_masks()

    with op.batch_alter_table('word', schema=None) as batch_op:
        batch_op.alter_column('mask', existing_type=sa.JSON(), nullable=False)

    with op.batch_alter_table('daily_puzzle', schema=None) as batch_op:
        batch_op.add_column(sa.Column('language', PUZZLE_LANGUAGE, server_default=KO, nullable=False))
        batch_op.drop_index(batch_op.f('puzzle_date'))
        batch_op.create_unique_constraint('uq_daily_puzzle_date_language', ['puzzle_date', 'language'])

    with op.batch_alter_table('guest', schema=None) as batch_op:
        batch_op.add_column(sa.Column('puzzle_language', PUZZLE_LANGUAGE, server_default=KO, nullable=False))

    # 통계도 "날짜당 하나"가 아니라 "날짜·언어당 하나"가 되므로 PK를 넓힌다.
    with op.batch_alter_table('daily_stats', schema=None) as batch_op:
        batch_op.add_column(sa.Column('language', PUZZLE_LANGUAGE, server_default=KO, nullable=False))
        batch_op.drop_constraint('PRIMARY', type_='primary')
        batch_op.create_primary_key('pk_daily_stats', ['puzzle_date', 'language'])


def downgrade():
    # 옛 스키마는 영어 데이터를 표현할 수 없다(퍼즐은 날짜당 하나, 통계 PK도 날짜
    # 하나). 그래서 되돌리기는 "ko 전용 상태로의 복귀"이고, en 행은 FK 순서대로
    # 지운다 — 남겨두면 유니크 인덱스를 다시 만들 수 없고, 언어 없는 배정 로직이
    # 영어 단어를 한국어 퍼즐로 뽑아버린다.
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM attempt WHERE puzzle_id IN "
            "(SELECT id FROM daily_puzzle WHERE language <> :ko)"
        ),
        {"ko": KO},
    )
    for table in ('daily_puzzle', 'word', 'daily_stats'):
        connection.execute(
            sa.text(f"DELETE FROM {table} WHERE language <> :ko"), {"ko": KO}
        )

    with op.batch_alter_table('daily_stats', schema=None) as batch_op:
        batch_op.drop_constraint('pk_daily_stats', type_='primary')
        batch_op.create_primary_key('pk_daily_stats', ['puzzle_date'])
        batch_op.drop_column('language')

    with op.batch_alter_table('guest', schema=None) as batch_op:
        batch_op.drop_column('puzzle_language')

    with op.batch_alter_table('daily_puzzle', schema=None) as batch_op:
        batch_op.drop_constraint('uq_daily_puzzle_date_language', type_='unique')
        batch_op.create_index(batch_op.f('puzzle_date'), ['puzzle_date'], unique=True)
        batch_op.drop_column('language')

    with op.batch_alter_table('word', schema=None) as batch_op:
        batch_op.drop_column('mask')
        batch_op.drop_column('language')


def _fill_word_masks():
    """기존 단어(전부 ko)의 가림을 저장 시점과 같은 규칙으로 채운다."""
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, language, answer FROM word")).fetchall()

    for row in rows:
        mask = build_mask(PuzzleLanguage(row.language), row.answer)
        connection.execute(
            sa.text("UPDATE word SET mask = :mask WHERE id = :id"),
            {"mask": json.dumps(mask, ensure_ascii=False), "id": row.id},
        )
