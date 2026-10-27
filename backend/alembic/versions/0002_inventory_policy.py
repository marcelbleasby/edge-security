"""Inventory and observation-only DNS policies.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('network_devices',
        sa.Column('id', sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column('sensor_id', sa.String(100), nullable=False),
        sa.Column('ip', sa.String(45), nullable=False),
        sa.Column('name', sa.String(150)),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('sensor_id', 'ip', name='uq_device_sensor_ip'))
    op.create_table('domain_policies',
        sa.Column('id', sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column('domain', sa.String(253), nullable=False),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('include_subdomains', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('description', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('domain', name='uq_domain_policy_domain'))

def downgrade():
    op.drop_table('domain_policies')
    op.drop_table('network_devices')
