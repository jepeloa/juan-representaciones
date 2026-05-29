"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(64), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(120), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('username', name='uq_users_username'),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('slug', sa.String(120), nullable=False),
        sa.UniqueConstraint('name', name='uq_suppliers_name'),
        sa.UniqueConstraint('slug', name='uq_suppliers_slug'),
    )
    op.create_index('ix_suppliers_name', 'suppliers', ['name'], unique=True)
    op.create_index('ix_suppliers_slug', 'suppliers', ['slug'], unique=True)

    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('supplier_id', 'name', name='uq_supplier_category'),
    )
    op.create_index('ix_categories_supplier_id', 'categories', ['supplier_id'])

    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('code', sa.String(120), nullable=True),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(14, 2), nullable=True),
        sa.Column('currency', sa.String(8), nullable=True),
        sa.Column('iva', sa.String(40), nullable=True),
        sa.Column('unit_per_pack', sa.Integer(), nullable=True),
        sa.Column('barcode', sa.String(60), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source_file', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_products_supplier_id', 'products', ['supplier_id'])
    op.create_index('ix_products_category_id', 'products', ['category_id'])
    op.create_index('ix_products_code', 'products', ['code'])
    op.create_index('ix_products_price', 'products', ['price'])
    op.create_index('ix_products_currency', 'products', ['currency'])
    op.create_index('ix_products_supplier_category', 'products', ['supplier_id', 'category_id'])
    op.create_index('ix_products_search', 'products', ['name', 'code'])

    op.create_table(
        'product_images',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('src', sa.String(500), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_product_images_product_id', 'product_images', ['product_id'])


def downgrade() -> None:
    op.drop_table('product_images')
    op.drop_table('products')
    op.drop_table('categories')
    op.drop_table('suppliers')
    op.drop_table('users')
