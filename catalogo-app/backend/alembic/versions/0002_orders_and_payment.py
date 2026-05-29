"""orders, payment conditions, settings

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payment_conditions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('multiplier', sa.Numeric(6, 4), nullable=False, server_default='1.0000'),
        sa.Column('days', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
    )

    op.create_table(
        'settings',
        sa.Column('key', sa.String(60), primary_key=True),
        sa.Column('value', sa.Text(), nullable=True),
    )

    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('payment_condition_id', sa.Integer(), nullable=True),
        sa.Column('payment_name', sa.String(120), nullable=True),
        sa.Column('payment_multiplier', sa.Numeric(6, 4), nullable=False, server_default='1.0000'),
        sa.Column('subtotal_ars', sa.Numeric(14, 2), nullable=False, server_default='0.00'),
        sa.Column('total_ars', sa.Numeric(14, 2), nullable=False, server_default='0.00'),
        sa.Column('subtotal_usd', sa.Numeric(14, 2), nullable=False, server_default='0.00'),
        sa.Column('total_usd', sa.Numeric(14, 2), nullable=False, server_default='0.00'),
        sa.Column('customer_notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_condition_id'], ['payment_conditions.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])

    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price_list', sa.Numeric(14, 2), nullable=False),
        sa.Column('unit_price_final', sa.Numeric(14, 2), nullable=False),
        sa.Column('currency', sa.String(8), nullable=False),
        sa.Column('line_total', sa.Numeric(14, 2), nullable=False),
        sa.Column('product_name', sa.String(500), nullable=False),
        sa.Column('product_code', sa.String(120), nullable=True),
        sa.Column('supplier_name', sa.String(120), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])


def downgrade() -> None:
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('settings')
    op.drop_table('payment_conditions')
