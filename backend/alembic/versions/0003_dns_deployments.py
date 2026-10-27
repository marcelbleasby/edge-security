"""Track Edge-owned Pi-hole entries and audit manual changes."""
from alembic import op
import sqlalchemy as sa
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('dns_deployments',
      sa.Column('id',sa.BigInteger(),sa.Identity(),primary_key=True),
      sa.Column('policy_id',sa.BigInteger(),sa.ForeignKey('domain_policies.id',ondelete='SET NULL')),
      sa.Column('domain',sa.String(253),nullable=False),
      sa.Column('action',sa.String(16),nullable=False),
      sa.Column('status',sa.String(24),nullable=False,server_default='deployed'),
      sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
      sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
      sa.UniqueConstraint('domain','action',name='uq_dns_deployment_domain_action'))
    op.create_table('dns_audit_logs',
      sa.Column('id',sa.BigInteger(),sa.Identity(),primary_key=True),
      sa.Column('event',sa.String(32),nullable=False),
      sa.Column('domain',sa.String(253)),
      sa.Column('detail',sa.Text()),
      sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table('dns_audit_logs')
    op.drop_table('dns_deployments')
