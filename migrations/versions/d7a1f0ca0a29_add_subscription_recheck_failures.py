"""add subscription recheck_failures

연속 재조회 실패 횟수 한 칸(티켓 13, 스펙 §A.8). Beat 가 3회 이상 쌓인 구독을
운영자에게 알린다.

`server_default='0'` 을 둔 이유: 이미 있는 구독 행에 NOT NULL 컬럼을 붙이려면
MySQL 이 채울 값을 알아야 한다. 기본값을 DB 에 남겨두면 마이그레이션만 돌린
상태(= 옛 코드가 아직 INSERT 하는 순간)에도 INSERT 가 깨지지 않는다 — 모델 쪽
`default=0` 은 파이썬 레벨이라 그 경로를 못 막는다.

Revision ID: d7a1f0ca0a29
Revises: dae1b5af0cf7
Create Date: 2026-10-14 09:18:47.181854

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7a1f0ca0a29'
down_revision = '94a83f12fddb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('subscription', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('recheck_failures', sa.Integer(), nullable=False, server_default='0')
        )


def downgrade():
    with op.batch_alter_table('subscription', schema=None) as batch_op:
        batch_op.drop_column('recheck_failures')
