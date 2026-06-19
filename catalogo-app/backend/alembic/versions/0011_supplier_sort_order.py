"""destacados de marcas: suppliers.sort_order

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-19

NULL = no destacada. Menor número = aparece primero en Marcas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('suppliers', sa.Column('sort_order', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('suppliers', 'sort_order')
