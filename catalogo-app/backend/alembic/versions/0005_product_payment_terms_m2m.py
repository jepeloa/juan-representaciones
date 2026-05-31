"""producto <-> condiciones de pago: muchos-a-muchos

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-31

Crea la tabla de asociación product_payment_terms y elimina la columna
products.payment_term_id (que estaba vacía: ningún producto tenía condición aún).
order_items.payment_term se mantiene (ahora guarda el snapshot unido por comas).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'product_payment_terms',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('payment_term_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_term_id'], ['payment_terms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'payment_term_id'),
    )
    # La columna single estaba vacía (feature recién agregada, sin asignaciones) -> sin migración de datos
    op.drop_constraint('fk_products_payment_term', 'products', type_='foreignkey')
    op.drop_index('ix_products_payment_term_id', table_name='products')
    op.drop_column('products', 'payment_term_id')


def downgrade() -> None:
    op.add_column('products', sa.Column('payment_term_id', sa.Integer(), nullable=True))
    op.create_index('ix_products_payment_term_id', 'products', ['payment_term_id'])
    op.create_foreign_key(
        'fk_products_payment_term', 'products', 'payment_terms',
        ['payment_term_id'], ['id'], ondelete='SET NULL',
    )
    op.drop_table('product_payment_terms')
