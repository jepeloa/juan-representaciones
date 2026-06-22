"""perfil de cliente + eventos de actividad

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-22

- client_profiles: datos de facturación/domicilio del cliente (todos opcionales).
- activity_events: registro de actividad del usuario (login, vistas, clics, compras).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0012'
down_revision: Union[str, None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'client_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(length=200), nullable=True),
        sa.Column('tax_id', sa.String(length=40), nullable=True),
        sa.Column('tax_condition', sa.String(length=60), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=60), nullable=True),
        sa.Column('contact_name', sa.String(length=120), nullable=True),
        sa.Column('address_street', sa.String(length=255), nullable=True),
        sa.Column('address_city', sa.String(length=120), nullable=True),
        sa.Column('address_state', sa.String(length=120), nullable=True),
        sa.Column('address_zip', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_client_profiles_user_id'), 'client_profiles', ['user_id'], unique=True)

    op.create_table(
        'activity_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=40), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('path', sa.String(length=255), nullable=True),
        sa.Column('ref_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_events_user_id'), 'activity_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_activity_events_event_type'), 'activity_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_activity_events_created_at'), 'activity_events', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_activity_events_created_at'), table_name='activity_events')
    op.drop_index(op.f('ix_activity_events_event_type'), table_name='activity_events')
    op.drop_index(op.f('ix_activity_events_user_id'), table_name='activity_events')
    op.drop_table('activity_events')
    op.drop_index(op.f('ix_client_profiles_user_id'), table_name='client_profiles')
    op.drop_table('client_profiles')
