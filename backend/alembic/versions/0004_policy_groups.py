"""Explicit desired Pi-hole groups per policy."""
from alembic import op
import sqlalchemy as sa
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('dns_policy_groups',
        sa.Column('policy_id',sa.BigInteger(),sa.ForeignKey('domain_policies.id',ondelete='CASCADE'),primary_key=True),
        sa.Column('group_ids',sa.JSON(),nullable=False))

def downgrade():
    op.drop_table('dns_policy_groups')
