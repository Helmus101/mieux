"""Add visits (anonymous usage counts)

Revision ID: 9c4a1d7b2e10
Revises: 2f560308c97e
Create Date: 2026-11-01 20:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4a1d7b2e10'
down_revision: Union[str, Sequence[str], None] = '2f560308c97e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('visits',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('day', sa.String(), nullable=False),
    sa.Column('surface', sa.String(), nullable=False),
    sa.Column('visitor', sa.String(), nullable=False),
    sa.Column('referrer', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('day', 'surface', 'visitor', name='uq_visit_day_surface_visitor')
    )
    op.create_index(op.f('ix_visits_day'), 'visits', ['day'], unique=False)
    op.create_index(op.f('ix_visits_visitor'), 'visits', ['visitor'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_visits_visitor'), table_name='visits')
    op.drop_index(op.f('ix_visits_day'), table_name='visits')
    op.drop_table('visits')
