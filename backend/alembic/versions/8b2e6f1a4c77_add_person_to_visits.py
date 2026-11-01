"""Add person hash to visits

Revision ID: 8b2e6f1a4c77
Revises: 5e8f0c1d2a34
Create Date: 2026-11-01 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b2e6f1a4c77'
down_revision: Union[str, Sequence[str], None] = '5e8f0c1d2a34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('visits', sa.Column('person', sa.String(), nullable=True))
    op.create_index(op.f('ix_visits_person'), 'visits', ['person'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_visits_person'), table_name='visits')
    op.drop_column('visits', 'person')
