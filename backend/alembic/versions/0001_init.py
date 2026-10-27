"""Create initial events and checkpoints tables.

Revision ID: 0001
Revises:
"""
from alembic import op
from app.models import Base
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables['security_events'], Base.metadata.tables['collector_checkpoints']])

def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, tables=[Base.metadata.tables['collector_checkpoints'], Base.metadata.tables['security_events']])
