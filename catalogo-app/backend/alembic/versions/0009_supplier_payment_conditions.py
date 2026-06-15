"""condiciones de pago por marca (supplier_payment_conditions N:N)

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'supplier_payment_conditions',
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('payment_condition_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_condition_id'], ['payment_conditions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('supplier_id', 'payment_condition_id'),
    )


def downgrade() -> None:
    op.drop_table('supplier_payment_conditions')
