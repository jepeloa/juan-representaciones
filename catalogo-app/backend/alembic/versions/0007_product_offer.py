"""ofertas: precio de oferta fijo + interruptor por producto

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-15

Agrega a products:
- offer_price (Numeric(14,2), nullable): precio rebajado fijo.
- is_offer (Boolean, default 0): si el producto está en oferta.
Un producto está "en oferta" cuando is_offer=1 y offer_price IS NOT NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('offer_price', sa.Numeric(14, 2), nullable=True))
    op.add_column('products', sa.Column('is_offer', sa.Boolean(), nullable=False, server_default='0'))
    op.create_index('ix_products_is_offer', 'products', ['is_offer'])


def downgrade() -> None:
    op.drop_index('ix_products_is_offer', table_name='products')
    op.drop_column('products', 'is_offer')
    op.drop_column('products', 'offer_price')
