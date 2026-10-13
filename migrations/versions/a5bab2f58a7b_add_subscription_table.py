"""add subscription table

광고 제거 구독 한 행 = 스토어가 마지막으로 말해준 상태(ADR 0003, 스펙 §A.8).

유니크는 `(store, store_key)` 하나뿐이고 이게 멱등의 전부다 — 앱이 같은 영수증을
구매 직후·복원·앱 시작마다 다시 올려도 행이 하나로 유지된다. `guest_id` 에는
유니크를 걸지 않는다(한 게스트가 애플·구글 양쪽에 구독을 들 수 있다).

`store_key` 는 Google purchaseToken 이 base64 수백 자라 512 로 뒀다. utf8mb4 로도
2048 바이트라 `(store, store_key)` 유니크 인덱스가 InnoDB 한계(3072) 안에 든다.

Revision ID: a5bab2f58a7b
Revises: f394da7f4d88
Create Date: 2026-10-14 07:00:28.226772

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5bab2f58a7b'
down_revision = 'f394da7f4d88'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('subscription',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('guest_id', sa.Integer(), nullable=False),
    sa.Column('store', sa.Enum('apple', 'google', name='subscriptionstore'), nullable=False),
    sa.Column('store_key', sa.String(length=512), nullable=False),
    sa.Column('product_id', sa.String(length=191), nullable=False),
    sa.Column('environment', sa.Enum('Sandbox', 'Production', name='subscriptionenvironment'), nullable=False),
    sa.Column('status', sa.Enum('active', 'grace', 'hold', 'expired', 'revoked', 'replaced', name='subscriptionstatus'), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('grace_expires_at', sa.DateTime(), nullable=True),
    sa.Column('last_verified_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['guest_id'], ['guest.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('store', 'store_key', name='uq_subscription_store_key')
    )


def downgrade():
    op.drop_table('subscription')
