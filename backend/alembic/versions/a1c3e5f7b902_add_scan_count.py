"""Add scan_count to users (the only data kept for a signed-in account)

Revision ID: a1c3e5f7b902
Revises: 8b2e6f1a4c77
Create Date: 2026-11-02 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1c3e5f7b902'
down_revision: Union[str, Sequence[str], None] = '8b2e6f1a4c77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('scan_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'scan_count')
