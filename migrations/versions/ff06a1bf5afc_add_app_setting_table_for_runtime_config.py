"""add app_setting table for runtime config

운영자가 재배포 없이 바꾸는 설정(점검 모드, 최소 앱 버전)을 담는 키·값 테이블
하나를 만든다. `GET /api/v1/config`가 이 행들을 읽는다(스펙 §A.10).

기본값 행은 넣지 않는다. 어떤 키가 있고 행이 없을 때 뭘 쓸지는
`app/services/app_config_service.py`가 들고 있어서, 여기서 같은 값을 한 벌 더
심으면 둘이 어긋날 수 있다 — 빈 테이블로도 /config가 정상 응답해야 한다.

Revision ID: ff06a1bf5afc
Revises: f394da7f4d88
Create Date: 2026-10-14 06:52:45.690962

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff06a1bf5afc'
down_revision = 'f394da7f4d88'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app_setting',
        # `key`는 MySQL 예약어라 컬럼 이름은 setting_key다 (모델 속성은 key).
        sa.Column('setting_key', sa.String(length=60), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('setting_key'),
    )


def downgrade():
    op.drop_table('app_setting')
