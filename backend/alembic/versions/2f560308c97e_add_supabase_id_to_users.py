"""Add supabase_id to users

Revision ID: 2f560308c97e
Revises: 7e13cf2439f3
Create Date: 2026-10-30 22:24:14.218146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f560308c97e'
down_revision: Union[str, Sequence[str], None] = '7e13cf2439f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('supabase_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_supabase_id'), 'users', ['supabase_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_supabase_id'), table_name='users')
    op.drop_column('users', 'supabase_id')
