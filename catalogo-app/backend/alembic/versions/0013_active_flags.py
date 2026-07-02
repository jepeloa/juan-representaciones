"""habilitar/inhabilitar marcas y productos

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-30

products.is_active y suppliers.is_active (default True). Si es False, no se
muestra al cliente. Inhabilitar una marca oculta también sus productos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('suppliers', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('products', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))
    op.create_index('ix_suppliers_is_active', 'suppliers', ['is_active'])
    op.create_index('ix_products_is_active', 'products', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_products_is_active', table_name='products')
    op.drop_index('ix_suppliers_is_active', table_name='suppliers')
    op.drop_column('products', 'is_active')
    op.drop_column('suppliers', 'is_active')
