"""producto <-> condiciones de pago (PaymentCondition) N:N; elimina PaymentTerm

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-31

- Elimina product_payment_terms y payment_terms (la feature de texto libre se descarta).
- Crea product_payment_conditions (producto <-> payment_conditions, N:N).
- order_items.payment_term se mantiene (snapshot de texto; ahora guarda nombres de condiciones).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Descartar la feature de texto libre (estaba sin uso real)
    op.drop_table('product_payment_terms')
    op.drop_table('payment_terms')

    # Nueva asociación producto <-> condiciones (multiplicador)
    op.create_table(
        'product_payment_conditions',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('payment_condition_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_condition_id'], ['payment_conditions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'payment_condition_id'),
    )


def downgrade() -> None:
    op.drop_table('product_payment_conditions')
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
    op.create_table(
        'product_payment_terms',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('payment_term_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_term_id'], ['payment_terms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'payment_term_id'),
    )
