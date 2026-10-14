"""add apple revocation retry table

애플 연결 철회(Sign in with Apple revoke)가 실패한 토큰을 담는 자리(스펙 §A.7).
계정 삭제는 애플 응답을 기다리지 않으므로, 실패한 철회만 이 테이블로 미뤄지고
Beat 가 매일 재시도한다 — 7일을 넘기면 폐기하고 운영자에게 알린다.

`guest_id` 가 없다: 이 행이 생기는 시점에 게스트 행은 이미 지워져 있다. 철회에
필요한 건 암호문 토큰과 그 토큰을 발급한 client 뿐이다(`account` 의 같은 두 컬럼).
토큰은 Fernet 암호문이라 길이가 평문보다 늘어서 String 대신 Text 다.

Revision ID: 94a83f12fddb
Revises: dae1b5af0cf7
Create Date: 2026-10-14 10:12:09.665418

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '94a83f12fddb'
down_revision = 'dae1b5af0cf7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('apple_revocation_retry',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('refresh_token_enc', sa.Text(), nullable=False),
    sa.Column('client_id', sa.String(length=191), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('apple_revocation_retry')
