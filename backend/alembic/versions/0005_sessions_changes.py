"""Persist admin sessions and DNS change snapshots.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('admin_sessions', sa.Column('token_hash',sa.String(64),primary_key=True), sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.create_table('dns_changes',sa.Column('id',sa.BigInteger(),sa.Identity(),primary_key=True),sa.Column('deployment_id',sa.BigInteger(),nullable=False),sa.Column('before_state',sa.JSON(),nullable=False),sa.Column('after_state',sa.JSON(),nullable=False),sa.Column('operation',sa.String(32),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('reverted_by',sa.BigInteger()))

def downgrade():
    op.drop_table('dns_changes')
    op.drop_table('admin_sessions')
