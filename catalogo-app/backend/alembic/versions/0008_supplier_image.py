"""marca: foto/logo (suppliers.image)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('suppliers', sa.Column('image', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('suppliers', 'image')
