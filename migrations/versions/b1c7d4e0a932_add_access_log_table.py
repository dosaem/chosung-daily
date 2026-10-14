"""add access log table

개인정보 처리 행위의 접속기록(티켓 36). 근거: 개인정보의 안전성 확보조치 기준
(개인정보보호위원회 고시 제2023-6호) 제8조(접속기록의 보관 및 점검).

INSERT 전용 테이블이라 `updated_at` 이 없다. `prev_hash`/`hash` 가 SHA-256 체인을
이루고, 둘 다 유니크다 — `hash` 는 같은 행이 두 번 들어가는 것을, `prev_hash` 는
체인이 두 갈래로 갈리는 것을 DB 가 막는다.
조회는 두 축뿐이다 — 보관 기간 삭제·월별 점검(`occurred_at`)과 행위별 집계
(`action`) — 그래서 인덱스도 그 두 개만 둔다.

Revision ID: b1c7d4e0a932
Revises: d7a1f0ca0a29
Create Date: 2026-10-14 16:05:11.482913

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b1c7d4e0a932'
down_revision = 'd7a1f0ca0a29'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('access_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('occurred_at', sa.DateTime(), nullable=False),
    sa.Column('actor', sa.String(length=191), nullable=False),
    sa.Column('remote_ip', sa.String(length=45), nullable=False),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('target', sa.String(length=191), nullable=True),
    sa.Column('result', sa.String(length=16), nullable=False),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('prev_hash', sa.String(length=64), nullable=False),
    sa.Column('hash', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('hash'),
    sa.UniqueConstraint('prev_hash')
    )
    with op.batch_alter_table('access_log', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_access_log_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_access_log_occurred_at'), ['occurred_at'], unique=False)


def downgrade():
    with op.batch_alter_table('access_log', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_access_log_occurred_at'))
        batch_op.drop_index(batch_op.f('ix_access_log_action'))

    op.drop_table('access_log')
