"""payment terms (free-text per-product condition, optionally linked to a supplier)

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-29

Aditiva: crea la tabla payment_terms y agrega products.payment_term_id +
order_items.payment_term. Todo nullable; no toca datos existentes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payment_terms',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('text', sa.String(length=500), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_payment_terms_supplier_id', 'payment_terms', ['supplier_id'])

    op.add_column('products', sa.Column('payment_term_id', sa.Integer(), nullable=True))
    op.create_index('ix_products_payment_term_id', 'products', ['payment_term_id'])
    op.create_foreign_key(
        'fk_products_payment_term', 'products', 'payment_terms',
        ['payment_term_id'], ['id'], ondelete='SET NULL',
    )

    op.add_column('order_items', sa.Column('payment_term', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('order_items', 'payment_term')
    op.drop_constraint('fk_products_payment_term', 'products', type_='foreignkey')
    op.drop_index('ix_products_payment_term_id', table_name='products')
    op.drop_column('products', 'payment_term_id')
    op.drop_index('ix_payment_terms_supplier_id', table_name='payment_terms')
    op.drop_table('payment_terms')
