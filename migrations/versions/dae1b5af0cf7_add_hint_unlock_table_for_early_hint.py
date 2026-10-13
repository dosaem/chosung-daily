"""add hint_unlock table for early hint

힌트 미리 보기(보상형 광고)를 쓴 사실을 담는 테이블 하나를 만든다(스펙 §A.5).
PK(guest_id, puzzle_id) 가 곧 "퍼즐당 1회" 규칙이라 별도 카운터 컬럼이 없다 —
행이 있으면 열린 것이다. 열림 여부는 기기가 아니라 게스트에 붙어서, 다른
기기에서 들어와도 `GET /api/v1/puzzles/today` 에 힌트가 계속 채워져 온다.

Revision ID: dae1b5af0cf7
Revises: a5bab2f58a7b
Create Date: 2026-10-14 08:25:22.070728

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dae1b5af0cf7'
down_revision = 'a5bab2f58a7b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'hint_unlock',
        sa.Column('guest_id', sa.Integer(), nullable=False),
        sa.Column('puzzle_id', sa.Integer(), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['guest_id'], ['guest.id']),
        sa.ForeignKeyConstraint(['puzzle_id'], ['daily_puzzle.id']),
        sa.PrimaryKeyConstraint('guest_id', 'puzzle_id'),
    )


def downgrade():
    op.drop_table('hint_unlock')
