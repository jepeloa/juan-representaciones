"""destacados: orden manual por sección (catalog_order, offer_order)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-19

NULL = no destacado. Menor número = aparece primero. Separado por sección.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('catalog_order', sa.Integer(), nullable=True))
    op.add_column('products', sa.Column('offer_order', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'offer_order')
    op.drop_column('products', 'catalog_order')
