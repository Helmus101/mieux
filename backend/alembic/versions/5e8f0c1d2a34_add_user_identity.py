"""Add name/city/platform to users

Revision ID: 5e8f0c1d2a34
Revises: 9c4a1d7b2e10
Create Date: 2026-11-01 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e8f0c1d2a34'
down_revision: Union[str, Sequence[str], None] = '9c4a1d7b2e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('city', sa.String(), nullable=True))
    op.add_column('users', sa.Column('postcode', sa.String(), nullable=True))
    op.add_column('users', sa.Column('platform', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_seen_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'last_seen_at')
    op.drop_column('users', 'platform')
    op.drop_column('users', 'postcode')
    op.drop_column('users', 'city')
    op.drop_column('users', 'name')
