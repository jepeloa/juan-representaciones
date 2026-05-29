"""add email tracking fields to orders

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('email_to', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('email_status', sa.String(20), nullable=False, server_default='pending'))
    op.add_column('orders', sa.Column('email_sent_at', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('email_error', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'email_error')
    op.drop_column('orders', 'email_sent_at')
    op.drop_column('orders', 'email_status')
    op.drop_column('orders', 'email_to')
