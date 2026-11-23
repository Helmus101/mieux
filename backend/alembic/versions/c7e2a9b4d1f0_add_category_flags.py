"""Add category flags (wrong-category reports)

Revision ID: c7e2a9b4d1f0
Revises: a1d3c5e7f901
Create Date: 2026-11-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c7e2a9b4d1f0'
down_revision: Union[str, Sequence[str], None] = 'a1d3c5e7f901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('category_flags',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('product_id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('placed_type', sa.String(), nullable=True),
    sa.Column('placed_category', sa.String(), nullable=True),
    sa.Column('suggested_type', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'product_id', name='uq_category_flag_user_product')
    )
    op.create_index(op.f('ix_category_flags_product_id'), 'category_flags', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_category_flags_product_id'), table_name='category_flags')
    op.drop_table('category_flags')
